/**
 * User profile page — server-rendered. Editing and avatar upload are a client island.
 */
import Link from 'next/link';
import ProfileCard from '@/components/ProfileCard';
import { fetchApi } from '@/lib/server-api';
import type { PublicProfile } from '@/types';

export default async function ProfilePage(props: { params: Promise<{ username: string }> }) {
    const { username } = await props.params;
    const profile = await fetchApi<PublicProfile>(`/api/profiles/${encodeURIComponent(username)}`);

    return (
        <div className="container">
            <ol className="breadcrumb">
                <li><Link href="/">Boards</Link></li>
                <li>{profile.username}</li>
            </ol>

            <div className="content-grid">
                <div>
                    <ProfileCard profile={profile} />
                </div>

                <aside>
                    <div className="form-card" style={{ marginTop: 112 }}>
                        <h3 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 8, color: 'var(--text-primary)' }}>
                            Quick Stats
                        </h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            <div>Topics: <strong>{profile.topic_count}</strong></div>
                            <div>Posts: <strong>{profile.post_count}</strong></div>
                            <div>Reputation: <strong>{profile.reputation_score}</strong></div>
                        </div>
                    </div>
                </aside>
            </div>
        </div>
    );
}
