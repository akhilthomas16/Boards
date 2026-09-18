/**
 * Profile header and about section. Client island: only the owner sees the edit and avatar controls.
 */
'use client';

import { useState } from 'react';
import api from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { PublicProfile } from '@/types';

export default function ProfileCard({ profile: initial }: { profile: PublicProfile }) {
    const { user } = useAuth();
    const [profile, setProfile] = useState(initial);
    const [editing, setEditing] = useState(false);
    const [bio, setBio] = useState(initial.bio);
    const [location, setLocation] = useState(initial.location);
    const [website, setWebsite] = useState(initial.website);
    const [saving, setSaving] = useState(false);
    const [avatarUploading, setAvatarUploading] = useState(false);
    const [error, setError] = useState('');

    const isOwnProfile = user?.username === profile.username;

    const handleSave = async () => {
        setSaving(true);
        setError('');
        try {
            setProfile(await api.patch<PublicProfile>('/api/profiles/me', { bio, location, website }));
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
        setError('');
        try {
            const formData = new FormData();
            formData.append('file', file);
            setProfile(await api.postMultipart<PublicProfile>('/api/profiles/me/avatar', formData));
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Upload failed');
        } finally {
            setAvatarUploading(false);
        }
    };

    return (
        <>
            {error && <div className="alert alert-error">{error}</div>}

            <div className="profile-card fade-in">
                <div className="profile-header">
                    <div className="profile-avatar-wrapper">
                        {profile.avatar_url ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={profile.avatar_url} alt={profile.username} className="profile-avatar-img" />
                        ) : (
                            <div className="profile-avatar-large">
                                {profile.username[0].toUpperCase()}
                            </div>
                        )}
                        {isOwnProfile && (
                            <label className="avatar-upload-btn">
                                {avatarUploading ? '⏳' : '📷'}
                                <input
                                    type="file"
                                    accept="image/jpeg,image/png,image/gif,image/webp"
                                    onChange={handleAvatarUpload}
                                    aria-label="Upload avatar"
                                    style={{ display: 'none' }}
                                />
                            </label>
                        )}
                    </div>
                    <div className="profile-info">
                        <h1 className="profile-username">{profile.username}</h1>
                        {profile.location && <p className="profile-location">📍 {profile.location}</p>}
                        <p className="profile-joined">
                            Joined {new Date(profile.date_joined).toLocaleDateString('en-US', { year: 'numeric', month: 'long' })}
                        </p>
                    </div>
                </div>

                <div className="profile-stats">
                    <div className="profile-stat">
                        <span className="stat-value">{profile.topic_count}</span>
                        <span className="stat-label">Topics</span>
                    </div>
                    <div className="profile-stat">
                        <span className="stat-value">{profile.post_count}</span>
                        <span className="stat-label">Posts</span>
                    </div>
                    <div className="profile-stat">
                        <span className="stat-value">{profile.reputation_score}</span>
                        <span className="stat-label">Reputation</span>
                    </div>
                </div>

                {profile.badges.length > 0 && (
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
                        {profile.badges.map((badge) => (
                            <span key={badge} style={{ fontSize: '0.75rem', background: 'var(--accent)', color: 'white', padding: '2px 8px', borderRadius: 12 }}>
                                {badge}
                            </span>
                        ))}
                    </div>
                )}

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
                                <label className="form-label" htmlFor="profile-bio">Bio</label>
                                <textarea
                                    id="profile-bio"
                                    className="form-textarea"
                                    value={bio}
                                    onChange={(e) => setBio(e.target.value)}
                                    placeholder="Tell us about yourself..."
                                    maxLength={500}
                                    rows={3}
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label" htmlFor="profile-location">Location</label>
                                <input
                                    id="profile-location"
                                    type="text"
                                    className="form-input"
                                    value={location}
                                    onChange={(e) => setLocation(e.target.value)}
                                    placeholder="City, Country"
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label" htmlFor="profile-website">Website</label>
                                <input
                                    id="profile-website"
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
                            <p style={{ color: profile.bio ? 'var(--text-secondary)' : 'var(--text-muted)', lineHeight: 1.6 }}>
                                {profile.bio || 'No bio yet.'}
                            </p>
                            {profile.website && (
                                <a href={profile.website} target="_blank" rel="noopener noreferrer"
                                    style={{ color: 'var(--accent)', fontSize: '0.875rem', display: 'block', marginTop: 8 }}>
                                    🔗 {profile.website}
                                </a>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </>
    );
}
