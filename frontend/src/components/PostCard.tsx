/**
 * Post card — the post, its reactions, and edit/delete for the author or a moderator.
 */
import { useState } from 'react';
import MarkdownEditor from './MarkdownEditor';
import MarkdownRenderer from './MarkdownRenderer';
import api from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { Post } from '@/types';

const OFFERED = ['👍', '❤️'] as const;  // must stay within the API's allowed emoji

interface PostCardProps {
    post: Post;
    myReactions?: string[];  // from the client-side lookup; server renders carry no cookie
    isFirst?: boolean;
    onQuote?: (text: string) => void;
    onChanged?: () => void;  // the post was edited or deleted
}

export default function PostCard({ post, myReactions, isFirst = false, onQuote, onChanged }: PostCardProps) {
    const { user } = useAuth();
    const [reactions, setReactions] = useState(post.reactions);
    const [mine, setMine] = useState<string[]>(myReactions ?? post.my_reactions);
    const [knownMine, setKnownMine] = useState(myReactions);
    const [message, setMessage] = useState(post.message);
    const [draft, setDraft] = useState(post.message);
    const [editing, setEditing] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');

    if (myReactions !== knownMine) {  // the lookup arrived, or the viewer changed
        setKnownMine(myReactions);
        setMine(myReactions ?? []);
    }

    const canModerate = !!user && (user.id === post.created_by.id || user.is_staff);

    const handleReact = async (emoji: string) => {
        if (!user) return;
        const had = mine.includes(emoji);

        setReactions(prev => ({ ...prev, [emoji]: Math.max(0, (prev[emoji] || 0) + (had ? -1 : 1)) }));
        setMine(prev => had ? prev.filter(e => e !== emoji) : [...prev, emoji]);

        try {
            await api.post(`/api/posts/${post.id}/react`, { emoji });
        } catch {
            setReactions(post.reactions);  // put the server's numbers back
            setMine(mine);
        }
    };

    const handleSaveEdit = async () => {
        setBusy(true);
        setError('');
        try {
            const updated = await api.patch<Post>(`/api/posts/${post.id}`, { message: draft });
            setMessage(updated.message);
            setEditing(false);
            onChanged?.();
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed to save');
        } finally {
            setBusy(false);
        }
    };

    const handleDelete = async () => {
        if (!confirm('Delete this post?')) return;
        setBusy(true);
        setError('');
        try {
            await api.delete(`/api/posts/${post.id}`);
            onChanged?.();
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed to delete');
            setBusy(false);
        }
    };

    return (
        <div className={`post-card ${isFirst ? 'post-card-first' : ''}`} id={`post-${post.id}`}>
            <div className="post-author">
                <div className="post-avatar">
                    {post.created_by.username[0].toUpperCase()}
                </div>
                <div className="post-author-info">
                    <span className="post-username">{post.created_by.username}</span>
                    {post.created_by.badges && post.created_by.badges.length > 0 && (
                        <div style={{ display: 'flex', gap: '4px', marginTop: '2px' }}>
                            {post.created_by.badges.map(b => (
                                <span key={b} style={{ fontSize: '0.65rem', background: 'var(--accent)', color: 'white', padding: '1px 4px', borderRadius: '4px' }}>
                                    {b}
                                </span>
                            ))}
                        </div>
                    )}
                    <span className="post-date" style={{ marginTop: '2px' }}>
                        {new Date(post.created_at).toLocaleDateString('en-US', {
                            year: 'numeric', month: 'short', day: 'numeric',
                            hour: '2-digit', minute: '2-digit',
                        })}
                    </span>
                </div>
            </div>

            {error && <div className="alert alert-error" style={{ marginTop: 12 }}>{error}</div>}

            {editing ? (
                <div style={{ marginTop: '12px' }}>
                    <MarkdownEditor value={draft} onChange={setDraft} ariaLabel="Edit post" />
                    <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 8 }}>
                        <button className="btn btn-ghost btn-sm" onClick={() => { setDraft(message); setEditing(false); }}>
                            Cancel
                        </button>
                        <button className="btn btn-primary btn-sm" onClick={handleSaveEdit} disabled={busy}>
                            {busy ? 'Saving...' : 'Save'}
                        </button>
                    </div>
                </div>
            ) : (
                <div className="post-content" style={{ marginTop: '12px', fontSize: '1rem', lineHeight: '1.6' }}>
                    <MarkdownRenderer content={message} />
                </div>
            )}

            <div className="post-actions" style={{ display: 'flex', gap: '16px', marginTop: '16px', borderTop: '1px solid var(--border)', paddingTop: '12px', alignItems: 'center' }}>
                <div className="post-reactions" style={{ display: 'flex', gap: '8px' }}>
                    {OFFERED.map(emoji => {
                        const count = reactions[emoji] || 0;
                        const reacted = mine.includes(emoji);
                        return (
                            <button
                                key={emoji}
                                onClick={() => handleReact(emoji)}
                                disabled={!user}
                                aria-pressed={reacted}
                                title={reacted ? `Remove your ${emoji}` : `React ${emoji}`}
                                style={{
                                    background: reacted ? 'var(--accent)' : 'var(--bg-card-hover)',
                                    color: reacted ? 'white' : 'var(--text-primary)',
                                    border: '1px solid var(--border)', borderRadius: '16px', padding: '2px 8px',
                                    fontSize: '0.875rem', cursor: user ? 'pointer' : 'default',
                                    display: 'flex', alignItems: 'center', gap: '4px',
                                }}
                            >
                                {emoji}{count > 0 && <span>{count}</span>}
                            </button>
                        );
                    })}
                </div>

                <div style={{ flex: 1 }}></div>

                {canModerate && !editing && (
                    <>
                        <button className="btn btn-ghost btn-sm" onClick={() => setEditing(true)} style={{ fontSize: '0.875rem' }}>
                            Edit
                        </button>
                        <button className="btn btn-ghost btn-sm" onClick={handleDelete} disabled={busy} style={{ fontSize: '0.875rem' }}>
                            Delete
                        </button>
                    </>
                )}

                {onQuote && (
                    <button
                        className="btn btn-ghost"
                        onClick={() => onQuote(message)}
                        style={{ padding: '6px 12px', fontSize: '0.875rem' }}
                    >
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ marginRight: '6px', verticalAlign: 'middle' }} xmlns="http://www.w3.org/2000/svg">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                        </svg>
                        Quote Reply
                    </button>
                )}
            </div>

            {post.updated_at && (
                <div className="post-edited">
                    Edited {new Date(post.updated_at).toLocaleDateString()}
                </div>
            )}
        </div>
    );
}
