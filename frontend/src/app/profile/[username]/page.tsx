/**
 * User profile page — view and edit profile, upload avatar.
 */
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import api, { getTokens } from '@/lib/api';
import { useAuth } from '@/lib/auth';

interface Profile {
    user_id: number;
    username: string;
    email: string;
    bio: string;
    avatar_url: string | null;
    location: string;
    website: string;
    post_count: number;
    topic_count: number;
    date_joined: string;
}

export default function ProfilePage() {
    const params = useParams();
    const username = params.username as string;
    const { user } = useAuth();
    const isOwnProfile = user?.username === username;

    const [profile, setProfile] = useState<Profile | null>(null);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState(false);
    const [bio, setBio] = useState('');
    const [location, setLocation] = useState('');
    const [website, setWebsite] = useState('');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const [avatarUploading, setAvatarUploading] = useState(false);

    useEffect(() => {
        api.get<Profile>(`/api/profiles/${username}`)
            .then((data) => {
                setProfile(data);
                setBio(data.bio);
                setLocation(data.location);
                setWebsite(data.website);
            })
            .catch((err) => setError(err.message))
            .finally(() => setLoading(false));
    }, [username]);

    const handleSave = async () => {
        setSaving(true);
        try {
            const updated = await api.patch<Profile>('/api/profiles/me', { bio, location, website });
            setProfile(updated);
            setEditing(false);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed to update');
        } finally {
            setSaving(false);
        }
    };

    const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setAvatarUploading(true);
        try {
            const formData = new FormData();
            formData.append('file', file);

            const { access } = getTokens();
            const res = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/profiles/me/avatar`,
                {
                    method: 'POST',
                    headers: { Authorization: `Bearer ${access}` },
                    body: formData,
                }
            );

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Upload failed');
            }

            const updated = await res.json();
            setProfile(updated);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Upload failed');
        } finally {
            setAvatarUploading(false);
        }
    };

    if (loading) {
        return (
            <div className="container">
                <div className="loading-center"><div className="spinner"></div></div>
            </div>
        );
    }

    if (error && !profile) {
        return (
            <div className="container">
                <div className="page-header">
                    <div className="alert alert-error">{error}</div>
                </div>
            </div>
        );
    }

    return (
        <div className="container">
            <ol className="breadcrumb">
                <li><Link href="/">Boards</Link></li>
                <li>{profile?.username}</li>
            </ol>

            <div className="content-grid">
                <div>
                    {error && <div className="alert alert-error">{error}</div>}

                    {/* Profile header */}
                    <div className="profile-card fade-in">
                        <div className="profile-header">
                            <div className="profile-avatar-wrapper">
                                {profile?.avatar_url ? (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img
                                        src={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}${profile.avatar_url}`}
                                        alt={profile.username}
                                        className="profile-avatar-img"
                                    />
                                ) : (
                                    <div className="profile-avatar-large">
                                        {profile?.username[0].toUpperCase()}
                                    </div>
                                )}
                                {isOwnProfile && (
                                    <label className="avatar-upload-btn">
                                        {avatarUploading ? '⏳' : '📷'}
                                        <input
                                            type="file"
                                            accept="image/jpeg,image/png,image/gif,image/webp"
                                            onChange={handleAvatarUpload}
                                            style={{ display: 'none' }}
                                        />
                                    </label>
                                )}
                            </div>
                            <div className="profile-info">
                                <h1 className="profile-username">{profile?.username}</h1>
                                {profile?.location && (
                                    <p className="profile-location">📍 {profile.location}</p>
                                )}
                                <p className="profile-joined">
                                    Joined {new Date(profile?.date_joined || '').toLocaleDateString('en-US', { year: 'numeric', month: 'long' })}
                                </p>
                            </div>
                        </div>

                        <div className="profile-stats">
                            <div className="profile-stat">
                                <span className="stat-value">{profile?.topic_count}</span>
                                <span className="stat-label">Topics</span>
                            </div>
                            <div className="profile-stat">
                                <span className="stat-value">{profile?.post_count}</span>
                                <span className="stat-label">Posts</span>
                            </div>
                        </div>

                        {/* Bio section */}
                        <div className="profile-section">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                                <h3 className="profile-section-title">About</h3>
                                {isOwnProfile && !editing && (
                                    <button className="btn btn-ghost btn-sm" onClick={() => setEditing(true)}>
                                        Edit Profile
                                    </button>
                                )}
                            </div>

                            {editing ? (
                                <div className="fade-in">
                                    <div className="form-group">
                                        <label className="form-label">Bio</label>
                                        <textarea
                                            className="form-textarea"
                                            value={bio}
                                            onChange={(e) => setBio(e.target.value)}
                                            placeholder="Tell us about yourself..."
                                            maxLength={500}
                                            rows={3}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Location</label>
                                        <input
                                            type="text"
                                            className="form-input"
                                            value={location}
                                            onChange={(e) => setLocation(e.target.value)}
                                            placeholder="City, Country"
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Website</label>
                                        <input
                                            type="url"
                                            className="form-input"
                                            value={website}
                                            onChange={(e) => setWebsite(e.target.value)}
                                            placeholder="https://example.com"
                                        />
                                    </div>
                                    <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                                        <button className="btn btn-ghost btn-sm" onClick={() => setEditing(false)}>Cancel</button>
                                        <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
                                            {saving ? 'Saving...' : 'Save'}
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div>
                                    <p style={{ color: profile?.bio ? 'var(--text-secondary)' : 'var(--text-muted)', lineHeight: 1.6 }}>
                                        {profile?.bio || 'No bio yet.'}
                                    </p>
                                    {profile?.website && (
                                        <a href={profile.website} target="_blank" rel="noopener noreferrer"
                                            style={{ color: 'var(--accent)', fontSize: '0.875rem', display: 'block', marginTop: 8 }}>
                                            🔗 {profile.website}
                                        </a>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <aside>
                    <div className="form-card" style={{ marginTop: 112 }}>
                        <h3 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 8, color: 'var(--text-primary)' }}>
                            Quick Stats
                        </h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            <div>Topics: <strong>{profile?.topic_count}</strong></div>
                            <div>Posts: <strong>{profile?.post_count}</strong></div>
                        </div>
                    </div>
                </aside>
            </div>
        </div>
    );
}
