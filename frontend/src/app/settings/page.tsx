/**
 * Account settings — profile fields and password. Client-side: everything here is the caller's own
 * data, and the auth cookie belongs to the API origin, so the server can't read it.
 */
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { Profile } from '@/types';

export default function SettingsPage() {
    const { user, isLoading } = useAuth();
    const [profile, setProfile] = useState<Profile | null>(null);
    const [loaded, setLoaded] = useState(false);
    const [bio, setBio] = useState('');
    const [location, setLocation] = useState('');
    const [website, setWebsite] = useState('');
    const [savingProfile, setSavingProfile] = useState(false);
    const [profileMessage, setProfileMessage] = useState('');
    const [profileError, setProfileError] = useState('');

    const [oldPassword, setOldPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [savingPassword, setSavingPassword] = useState(false);
    const [passwordMessage, setPasswordMessage] = useState('');
    const [passwordError, setPasswordError] = useState('');

    useEffect(() => {
        if (!user || loaded) return;
        api.get<Profile>('/api/profiles/me')
            .then((data) => {
                setProfile(data);
                setBio(data.bio);
                setLocation(data.location);
                setWebsite(data.website);
                setLoaded(true);
            })
            .catch((err) => setProfileError(err.message));
    }, [user, loaded]);

    if (isLoading) {
        return <div className="container"><div className="loading-center"><div className="spinner"></div></div></div>;
    }

    if (!user) {
        return (
            <div className="container" style={{ paddingTop: 48 }}>
                <div className="form-card" style={{ textAlign: 'center', padding: 40 }}>
                    <p style={{ marginBottom: 16 }}>Log in to change your settings.</p>
                    <Link href="/auth/login" className="btn btn-primary">Log in</Link>
                </div>
            </div>
        );
    }

    // The form is only rendered once the profile is here: a late response would otherwise
    // overwrite whatever the user had already typed into it.
    if (!loaded && !profileError) {
        return <div className="container"><div className="loading-center"><div className="spinner"></div></div></div>;
    }

    const saveProfile = async (e: React.FormEvent) => {
        e.preventDefault();
        setSavingProfile(true);
        setProfileError('');
        setProfileMessage('');
        try {
            setProfile(await api.patch<Profile>('/api/profiles/me', { bio, location, website }));
            setProfileMessage('Profile saved.');
        } catch (err: unknown) {
            setProfileError(err instanceof Error ? err.message : 'Failed to save');
        } finally {
            setSavingProfile(false);
        }
    };

    const changePassword = async (e: React.FormEvent) => {
        e.preventDefault();
        setPasswordError('');
        setPasswordMessage('');
        if (newPassword !== confirmPassword) {
            setPasswordError('New passwords do not match');
            return;
        }
        setSavingPassword(true);
        try {
            await api.post('/api/auth/change-password', { old_password: oldPassword, new_password: newPassword });
            setPasswordMessage('Password changed. Other devices have been logged out.');
            setOldPassword('');
            setNewPassword('');
            setConfirmPassword('');
        } catch (err: unknown) {
            setPasswordError(err instanceof Error ? err.message : 'Failed to change password');
        } finally {
            setSavingPassword(false);
        }
    };

    return (
        <div className="container" style={{ maxWidth: 720 }}>
            <div className="page-header">
                <h1 className="page-title">Settings</h1>
                <p className="page-subtitle">
                    Signed in as <Link href={`/profile/${user.username}`}>{user.username}</Link>
                    {profile?.email ? ` · ${profile.email}` : ''}
                </p>
            </div>

            <div className="form-card" style={{ marginBottom: 24 }}>
                <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 16 }}>Profile</h2>
                {profileError && <div className="alert alert-error">{profileError}</div>}
                {profileMessage && <div className="alert">{profileMessage}</div>}
                <form onSubmit={saveProfile}>
                    <div className="form-group">
                        <label className="form-label" htmlFor="settings-bio">Bio</label>
                        <textarea
                            id="settings-bio"
                            className="form-textarea"
                            value={bio}
                            onChange={(e) => setBio(e.target.value)}
                            maxLength={500}
                            rows={3}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="settings-location">Location</label>
                        <input id="settings-location" type="text" className="form-input"
                            value={location} onChange={(e) => setLocation(e.target.value)} />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="settings-website">Website</label>
                        <input id="settings-website" type="url" className="form-input" placeholder="https://example.com"
                            value={website} onChange={(e) => setWebsite(e.target.value)} />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <button type="submit" className="btn btn-primary" disabled={savingProfile}>
                            {savingProfile ? 'Saving...' : 'Save profile'}
                        </button>
                    </div>
                </form>
            </div>

            <div className="form-card">
                <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 16 }}>Password</h2>
                {passwordError && <div className="alert alert-error">{passwordError}</div>}
                {passwordMessage && <div className="alert">{passwordMessage}</div>}
                <form onSubmit={changePassword}>
                    <div className="form-group">
                        <label className="form-label" htmlFor="settings-old-password">Current password</label>
                        <input id="settings-old-password" type="password" className="form-input" required
                            autoComplete="current-password"
                            value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="settings-new-password">New password</label>
                        <input id="settings-new-password" type="password" className="form-input" required
                            autoComplete="new-password" minLength={8}
                            value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="settings-confirm-password">Confirm new password</label>
                        <input id="settings-confirm-password" type="password" className="form-input" required
                            autoComplete="new-password"
                            value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <button type="submit" className="btn btn-primary" disabled={savingPassword}>
                            {savingPassword ? 'Changing...' : 'Change password'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
