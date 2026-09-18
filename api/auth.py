"""
JWT authentication in httpOnly cookies — login, refresh rotation, logout, signup, password flows.
"""
import hmac
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.security import APIKeyCookie, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail

from .limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
access_cookie = APIKeyCookie(name=ACCESS_COOKIE, auto_error=False)

REFRESH_REUSE_GRACE_SECONDS = 30
OTP_TTL_SECONDS = 600
OTP_MAX_ATTEMPTS = 5


# =============================================================================
# SCHEMAS
# =============================================================================

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# =============================================================================
# TOKEN UTILS
# =============================================================================

def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


def _refresh_lifetime() -> timedelta:
    return timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)


def _password_fingerprint(user: User) -> str:
    """Changes whenever the password does, so a password change or reset kills every existing token."""
    return user.get_session_auth_hash()[:16]


def _encode(claims: dict, lifetime: timedelta, token_type: str) -> str:
    expire = datetime.now(timezone.utc) + lifetime
    return jwt.encode({**claims, "type": token_type, "exp": expire},
                      settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def issue_tokens(response: Response, user: User, family: str | None = None) -> None:
    """Set a fresh access + refresh cookie pair. `family` ties every rotation of one login together."""
    family = family or uuid.uuid4().hex
    jti = uuid.uuid4().hex
    claims = {"sub": user.username, "user_id": user.id, "fam": family, "pwd": _password_fingerprint(user)}
    access_lifetime = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_lifetime = _refresh_lifetime()

    cache.set(f"auth:refresh:{jti}", family, timeout=int(refresh_lifetime.total_seconds()))

    cookie = {"httponly": True, "secure": not settings.DEBUG, "samesite": "lax"}
    response.set_cookie(ACCESS_COOKIE, _encode(claims, access_lifetime, "access"),
                        max_age=int(access_lifetime.total_seconds()), path="/api", **cookie)
    response.set_cookie(REFRESH_COOKIE, _encode({**claims, "jti": jti}, refresh_lifetime, "refresh"),
                        max_age=int(refresh_lifetime.total_seconds()), path="/api/auth", **cookie)


def clear_tokens(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/api")
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")


def revoke_family(family: str) -> None:
    cache.set(f"auth:revoked:{family}", 1, timeout=int(_refresh_lifetime().total_seconds()))


def verify_token(token: str | None, token_type: str = "access") -> dict:
    if not token:
        raise _unauthorized()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise _unauthorized()
    if payload.get("type") != token_type:
        raise HTTPException(status_code=401, detail="Invalid token type")
    if cache.get(f"auth:revoked:{payload.get('fam')}"):
        raise _unauthorized()
    return payload


def user_for_payload(payload: dict) -> User:
    """Resolve on the immutable user_id; reject inactive users and tokens minted before a password change."""
    user = User.objects.filter(pk=payload.get("user_id"), is_active=True).first()
    if user is None or not hmac.compare_digest(str(payload.get("pwd", "")).encode(),
                                               _password_fingerprint(user).encode()):
        raise _unauthorized()
    return user


def user_from_token(token: str | None, token_type: str = "access") -> User:
    return user_for_payload(verify_token(token, token_type))


def check_password_strength(password: str, user: User) -> None:
    """Run AUTH_PASSWORD_VALIDATORS; 400 with every failed rule."""
    try:
        validate_password(password, user)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=" ".join(e.messages))


# =============================================================================
# DEPENDENCIES
# =============================================================================

def get_current_user(token: str | None = Depends(access_cookie)) -> User:
    """Get the current authenticated user from the access-token cookie."""
    return user_from_token(token)


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/token", response_model=UserResponse)
@limiter.limit("5/minute")
def login(request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    """Login with username/password; sets the token cookies and returns the user."""
    # authenticate() rejects inactive users and hashes even for unknown usernames (no timing oracle).
    user = authenticate(username=form_data.username, password=form_data.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    issue_tokens(response, user)
    return user


@router.post("/refresh", response_model=UserResponse)
@limiter.limit("10/minute")
def refresh(request: Request, response: Response):
    """Rotate the token pair. Each refresh token works once; replaying one revokes its whole family."""
    payload = verify_token(request.cookies.get(REFRESH_COOKIE), token_type="refresh")
    user = user_for_payload(payload)
    jti, family = payload.get("jti"), payload.get("fam")

    if not cache.delete(f"auth:refresh:{jti}"):
        # ponytail: the grace window lets two tabs refresh at once without a logout; a replay after it
        # revokes the family. Two tabs racing inside the window still leaves the loser with a 401.
        if not cache.get(f"auth:used:{jti}"):
            revoke_family(family)
        raise _unauthorized()
    cache.set(f"auth:used:{jti}", 1, timeout=REFRESH_REUSE_GRACE_SECONDS)
    issue_tokens(response, user, family)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response):
    """Revoke this login's token family and clear the cookies."""
    for name, token_type in ((REFRESH_COOKIE, "refresh"), (ACCESS_COOKIE, "access")):
        try:
            revoke_family(verify_token(request.cookies.get(name), token_type)["fam"])
            break
        except HTTPException:
            continue
    clear_tokens(response)


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def signup(request: Request, user_data: UserCreate):
    """Create a new user account."""
    email = user_data.email.lower()
    if User.objects.filter(username=user_data.username).exists():
        raise HTTPException(status_code=400, detail="Username already taken")
    if User.objects.filter(email__iexact=email).exists():
        raise HTTPException(status_code=400, detail="Email already registered")
    check_password_strength(user_data.password, User(username=user_data.username, email=email))

    return User.objects.create_user(username=user_data.username, email=email, password=user_data.password)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user's profile."""
    return current_user


@router.post("/change-password")
@limiter.limit("5/minute")
def change_password(
    request: Request,
    response: Response,
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
):
    """Change the password. Every other session is logged out; this one gets fresh cookies."""
    if not current_user.check_password(data.old_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    check_password_strength(data.new_password, current_user)

    current_user.set_password(data.new_password)
    current_user.save()
    issue_tokens(response, current_user)
    return {"message": "Password changed successfully"}


# =============================================================================
# FORGOT PASSWORD
# =============================================================================

class ForgotPasswordRequest(BaseModel):
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str


def _otp_keys(email: str) -> tuple[str, str]:
    email = email.strip().lower()
    return f"otp:{email}", f"otp:attempts:{email}"


def send_otp_email(email: str, otp: str) -> None:
    send_mail(
        subject="Your password reset code",
        message=f"Your password reset code is: {otp}\n\nThis code expires in {OTP_TTL_SECONDS // 60} minutes.",
        from_email=None,  # DEFAULT_FROM_EMAIL
        recipient_list=[email],
        fail_silently=False,
    )


def _send_otp(email: str, otp: str) -> None:
    try:
        send_otp_email(email, otp)
    except Exception:
        logger.exception("Failed to send password reset code")


def _check_otp(email: str, otp: str) -> int:
    """Return the user id the code was issued for. Five wrong guesses burn the code."""
    code_key, attempts_key = _otp_keys(email)
    invalid = HTTPException(status_code=400, detail="Invalid or expired code")
    try:
        attempts = cache.incr(attempts_key)  # atomic, so parallel guesses can't share one count
    except ValueError:  # no code issued, or it expired
        raise invalid
    stored = cache.get(code_key)
    if stored is None or attempts > OTP_MAX_ATTEMPTS:
        cache.delete_many([code_key, attempts_key])
        raise invalid
    if not hmac.compare_digest(stored["otp"].encode(), otp.encode()):
        raise invalid
    return stored["user_id"]


@router.post("/forgot-password")
@limiter.limit("3/minute")
def forgot_password(request: Request, data: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    """Email a 6-digit reset code. Same response whether or not the account exists."""
    message = {"message": "If an account with that email exists, a reset code has been sent."}
    user = User.objects.filter(email__iexact=data.email.strip(), is_active=True).first()
    if user is None:
        return message

    otp = f"{secrets.randbelow(900000) + 100000}"
    code_key, attempts_key = _otp_keys(data.email)
    cache.set(code_key, {"otp": otp, "user_id": user.id}, timeout=OTP_TTL_SECONDS)
    cache.set(attempts_key, 0, timeout=OTP_TTL_SECONDS)

    # After the response, so a known email isn't measurably slower than an unknown one.
    background_tasks.add_task(_send_otp, user.email, otp)
    return message


@router.post("/verify-otp")
@limiter.limit("5/minute")
def verify_otp(request: Request, data: VerifyOTPRequest):
    """Pre-check a code before the reset form. Counts as an attempt; does not consume the code."""
    _check_otp(data.email, data.otp)
    return {"message": "Code verified"}


@router.post("/reset-password")
@limiter.limit("3/minute")
def reset_password(request: Request, data: ResetPasswordRequest):
    """Reset the password with a valid code. Logs out every session."""
    user_id = _check_otp(data.email, data.otp)
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    check_password_strength(data.new_password, user)
    user.set_password(data.new_password)
    user.save()
    cache.delete_many(list(_otp_keys(data.email)))
    return {"message": "Password has been reset successfully"}
