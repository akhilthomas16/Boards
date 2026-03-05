'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

type Step = 'email' | 'otp' | 'done';

export default function ForgotPasswordPage() {
    const router = useRouter();
    const [step, setStep] = useState<Step>('email');
    const [email, setEmail] = useState('');
    const [otp, setOtp] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');
    const [loading, setLoading] = useState(false);

    const handleRequestOTP = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const res = await fetch(`${API_BASE}/api/auth/forgot-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Request failed');
            setMessage(data.message);
            setStep('otp');
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Request failed');
        } finally {
            setLoading(false);
        }
    };

    const handleResetPassword = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (newPassword !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }
        if (newPassword.length < 8) {
            setError('Password must be at least 8 characters');
            return;
        }

        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/api/auth/reset-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, otp, new_password: newPassword }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Reset failed');
            setStep('done');
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Reset failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-card">
                {step === 'email' && (
                    <>
                        <h1 className="auth-title">Forgot Password</h1>
                        <p className="auth-subtitle">
                            Enter your email and we&apos;ll send you a reset code
                        </p>

                        {error && <div className="alert alert-error">{error}</div>}

                        <form onSubmit={handleRequestOTP}>
                            <div className="form-group">
                                <label className="form-label" htmlFor="fp-email">Email</label>
                                <input
                                    id="fp-email"
                                    type="email"
                                    className="form-input"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="Enter your email"
                                    required
                                    autoComplete="email"
                                />
                            </div>
                            <button
                                type="submit"
                                className="btn btn-primary"
                                style={{ width: '100%', marginTop: 8 }}
                                disabled={loading}
                            >
                                {loading ? 'Sending...' : 'Send Reset Code'}
                            </button>
                        </form>
                    </>
                )}

                {step === 'otp' && (
                    <>
                        <h1 className="auth-title">Reset Password</h1>
                        <p className="auth-subtitle">
                            Enter the 6-digit code sent to {email}
                        </p>

                        {error && <div className="alert alert-error">{error}</div>}
                        {message && <div className="alert alert-success">{message}</div>}

                        <form onSubmit={handleResetPassword}>
                            <div className="form-group">
                                <label className="form-label" htmlFor="fp-otp">Reset Code</label>
                                <input
                                    id="fp-otp"
                                    type="text"
                                    className="form-input"
                                    value={otp}
                                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                    placeholder="123456"
                                    required
                                    maxLength={6}
                                    inputMode="numeric"
                                    autoComplete="one-time-code"
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label" htmlFor="fp-password">New Password</label>
                                <input
                                    id="fp-password"
                                    type="password"
                                    className="form-input"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    placeholder="At least 8 characters"
                                    required
                                    minLength={8}
                                    autoComplete="new-password"
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label" htmlFor="fp-confirm">Confirm Password</label>
                                <input
                                    id="fp-confirm"
                                    type="password"
                                    className="form-input"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    placeholder="Confirm your password"
                                    required
                                    minLength={8}
                                    autoComplete="new-password"
                                />
                            </div>
                            <button
                                type="submit"
                                className="btn btn-primary"
                                style={{ width: '100%', marginTop: 8 }}
                                disabled={loading || otp.length !== 6}
                            >
                                {loading ? 'Resetting...' : 'Reset Password'}
                            </button>
                        </form>

                        <div className="auth-footer">
                            <button
                                onClick={() => { setStep('email'); setError(''); setMessage(''); }}
                                className="btn-link"
                                style={{ background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: '0.875rem' }}
                            >
                                Use a different email
                            </button>
                        </div>
                    </>
                )}

                {step === 'done' && (
                    <>
                        <h1 className="auth-title">Password Reset</h1>
                        <p className="auth-subtitle">
                            Your password has been reset successfully.
                        </p>
                        <button
                            className="btn btn-primary"
                            style={{ width: '100%', marginTop: 16 }}
                            onClick={() => router.push('/auth/login')}
                        >
                            Sign In
                        </button>
                    </>
                )}

                <div className="auth-footer">
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                        Remember your password? <Link href="/auth/login">Sign In</Link>
                    </span>
                </div>
            </div>
        </div>
    );
}
