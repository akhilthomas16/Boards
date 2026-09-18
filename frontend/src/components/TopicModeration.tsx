/**
 * Pin, lock and delete a topic. Rendered for staff only.
 */
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { Topic } from '@/types';

interface TopicModerationProps {
    topicId: number;
    boardId: number;
    isPinned: boolean;
    isLocked: boolean;
}

export default function TopicModeration({ topicId, boardId, isPinned, isLocked }: TopicModerationProps) {
    const router = useRouter();
    const { user } = useAuth();
    const [flags, setFlags] = useState({ is_pinned: isPinned, is_locked: isLocked });
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');

    if (!user?.is_staff) return null;

    const toggle = async (field: 'is_pinned' | 'is_locked') => {
        setBusy(true);
        setError('');
        try {
            const updated = await api.patch<Topic>(`/api/topics/${topicId}`, { [field]: !flags[field] });
            setFlags({ is_pinned: updated.is_pinned, is_locked: updated.is_locked });
            router.refresh();
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed');
        } finally {
            setBusy(false);
        }
    };

    const remove = async () => {
        if (!confirm('Delete this topic and all of its posts?')) return;
        setBusy(true);
        try {
            await api.delete(`/api/topics/${topicId}`);
            router.push(`/boards/${boardId}`);
            router.refresh();
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed to delete');
            setBusy(false);
        }
    };

    return (
        <div className="form-card" style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16, padding: 12 }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Moderator
            </span>
            <button className="btn btn-ghost btn-sm" onClick={() => toggle('is_pinned')} disabled={busy} aria-pressed={flags.is_pinned}>
                {flags.is_pinned ? 'Unpin' : 'Pin'}
            </button>
            <button className="btn btn-ghost btn-sm" onClick={() => toggle('is_locked')} disabled={busy} aria-pressed={flags.is_locked}>
                {flags.is_locked ? 'Unlock' : 'Lock'}
            </button>
            <button className="btn btn-ghost btn-sm" onClick={remove} disabled={busy}>Delete topic</button>
            {error && <span className="alert alert-error" style={{ padding: '4px 8px', margin: 0 }}>{error}</span>}
        </div>
    );
}
