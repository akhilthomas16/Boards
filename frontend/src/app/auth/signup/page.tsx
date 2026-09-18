/**
 * Signup page — create account with JWT auth.
 */
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function SignupPage() {
    const router = useRouter();
    const { signup, login } = useAuth();
    const [step, setStep] = useState<'details' | 'verify'>('details');
    const [code, setCode] = useState('');
    const [message, setMessage] = useState('');
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        if (password.length < 8) {
            setError('Password must be at least 8 characters');
            return;
        }

        setLoading(true);

        try {
            await signup(username, email, password);
            setMessage(`We emailed a 6-digit code to ${email}. Enter it to activate your account.`);
            setStep('verify');
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Signup failed');
        } finally {
            setLoading(false);
        }
    };

    const handleVerify = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await api.post('/api/auth/verify-email', { email, code });
            await login(username, password);  // the account is active now
            router.push('/');
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Verification failed');
        } finally {
            setLoading(false);
        }
    };

    const handleResend = async () => {
        setError('');
        try {
            await api.post('/api/auth/resend-verification', { email });
            setMessage('If that account still needs verifying, a new code is on its way.');
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Could not resend the code');
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-card">
                <h1 className="auth-title">{step === 'details' ? 'Create an Account' : 'Verify your email'}</h1>
                <p className="auth-subtitle">
                    {step === 'details' ? 'Join Hash Out and start discussing' : message}
                </p>

                {error && <div className="alert alert-error">{error}</div>}

                {step === 'verify' ? (
                    <form onSubmit={handleVerify}>
                        <div className="form-group">
                            <label className="form-label" htmlFor="signup-code">Verification code</label>
                            <input
                                id="signup-code"
                                type="text"
                                inputMode="numeric"
                                className="form-input"
                                value={code}
                                onChange={(e) => setCode(e.target.value)}
                                placeholder="6-digit code"
                                required
                                maxLength={6}
                                autoComplete="one-time-code"
                            />
                        </div>
                        <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: 8 }} disabled={loading}>
                            {loading ? 'Verifying...' : 'Verify and sign in'}
                        </button>
                        <button type="button" className="btn btn-ghost btn-sm" style={{ width: '100%', marginTop: 8 }} onClick={handleResend}>
                            Resend code
                        </button>
                    </form>
                ) : (
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label className="form-label" htmlFor="signup-username">Username</label>
                        <input
                            id="signup-username"
                            type="text"
                            className="form-input"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="Choose a username"
                            required
                            autoComplete="username"
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="signup-email">Email</label>
                        <input
                            id="signup-email"
                            type="email"
                            className="form-input"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="Enter your email"
                            required
                            autoComplete="email"
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="signup-password">Password</label>
                        <input
                            id="signup-password"
                            type="password"
                            className="form-input"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Create a password"
                            required
                            minLength={8}
                            autoComplete="new-password"
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="signup-confirm">Confirm Password</label>
                        <input
                            id="signup-confirm"
                            type="password"
                            className="form-input"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            placeholder="Confirm your password"
                            required
                            autoComplete="new-password"
                        />
                    </div>
                    <button
                        type="submit"
                        className="btn btn-primary"
                        style={{ width: '100%', marginTop: 8 }}
                        disabled={loading}
                    >
                        {loading ? 'Creating account...' : 'Create Account'}
                    </button>
                </form>
                )}

                <div className="auth-footer">
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                        Already have an account? <Link href="/auth/login">Sign In</Link>
                    </span>
                </div>
            </div>
        </div>
    );
}
