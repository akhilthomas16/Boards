/**
 * Notifications — the full list, paginated. Client-side: it is the caller's own data.
 */
'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { useWebSockets } from '@/lib/WebSocketProvider';
import type { Notification } from '@/types';

interface NotificationPage {
    count: number;
    page: number;
    total_pages: number;
    results: Notification[];
}

export default function NotificationsPage() {
    const { user, isLoading } = useAuth();
    const { refreshUnread } = useWebSockets();
    const [page, setPage] = useState(1);
    const [data, setData] = useState<NotificationPage | null>(null);
    const [error, setError] = useState('');

    const load = useCallback((which: number) => {
        api.get<NotificationPage>(`/api/notifications/?page=${which}&page_size=20`)
            .then(setData)
            .catch((err) => setError(err.message));
    }, []);

    useEffect(() => {
        if (user) load(page);
    }, [user, page, load]);

    if (isLoading) {
        return <div className="container"><div className="loading-center"><div className="spinner"></div></div></div>;
    }

    if (!user) {
        return (
            <div className="container" style={{ paddingTop: 48 }}>
                <div className="form-card" style={{ textAlign: 'center', padding: 40 }}>
                    <p style={{ marginBottom: 16 }}>Log in to see your notifications.</p>
                    <Link href="/auth/login" className="btn btn-primary">Log in</Link>
                </div>
            </div>
        );
    }

    const markAllRead = async () => {
        await api.post('/api/notifications/read-all', {});
        refreshUnread();
        load(page);
    };

    const remove = async (id: number) => {
        await api.delete(`/api/notifications/${id}`);
        refreshUnread();
        load(page);
    };

    const open = async (n: Notification) => {
        if (!n.is_read) {
            await api.post(`/api/notifications/${n.id}/read`, {});
            refreshUnread();
        }
    };

    return (
        <div className="container" style={{ maxWidth: 720 }}>
            <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                <div>
                    <h1 className="page-title">Notifications</h1>
                    <p className="page-subtitle">{data?.count ?? 0} in total</p>
                </div>
                <button className="btn btn-ghost btn-sm" onClick={markAllRead}>Mark all read</button>
            </div>

            {error && <div className="alert alert-error">{error}</div>}

            {data && data.results.length === 0 && (
                <div className="form-card" style={{ textAlign: 'center', padding: 40 }}>
                    <p style={{ color: 'var(--text-secondary)' }}>Nothing here yet.</p>
                </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {data?.results.map((n) => (
                    <div
                        key={n.id}
                        className="form-card"
                        style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 12, opacity: n.is_read ? 0.65 : 1 }}
                    >
                        <Link href={n.link || '/'} onClick={() => open(n)} style={{ flex: 1, color: 'inherit', textDecoration: 'none' }}>
                            <strong>{n.actor}</strong> {n.message}
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                                {new Date(n.created_at).toLocaleString()}
                            </div>
                        </Link>
                        <button className="btn btn-ghost btn-sm" onClick={() => remove(n.id)} aria-label={`Delete notification from ${n.actor}`}>
                            ✕
                        </button>
                    </div>
                ))}
            </div>

            {data && data.total_pages > 1 && (
                <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 24 }}>
                    <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                        Previous
                    </button>
                    <span style={{ alignSelf: 'center', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                        Page {data.page} of {data.total_pages}
                    </span>
                    <button className="btn btn-ghost btn-sm" disabled={page >= data.total_pages} onClick={() => setPage(page + 1)}>
                        Next
                    </button>
                </div>
            )}
        </div>
    );
}
