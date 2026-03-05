/**
 * Post card component — displays a forum post with author info.
 */
import MarkdownRenderer from './MarkdownRenderer';
import { useState } from 'react';
import { getTokens } from '@/lib/api';

interface PostCardProps {
    id: number;
    message: string;
    createdBy: { id: number; username: string; badges?: string[] };
    createdAt: string;
    updatedAt?: string | null;
    isFirst?: boolean;
    onQuote?: (text: string) => void;
    initialReactions?: Record<string, number>;
}

export default function PostCard({
    id, message, createdBy, createdAt, updatedAt, isFirst = false, onQuote, initialReactions = {},
}: PostCardProps) {
    const [reactions, setReactions] = useState<Record<string, number>>(initialReactions);

    const handleReact = async (emoji: string) => {
        const tokens = getTokens();
        if (!tokens) return;

        // Optimistic UI update
        const currentCount = reactions[emoji] || 0;
        setReactions({ ...reactions, [emoji]: currentCount + 1 });

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
            const res = await fetch(`${apiUrl}/api/posts/${id}/react`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${tokens.access}`
                },
                body: JSON.stringify({ emoji }),
            });
            const data = await res.json();
            if (data.action === 'removed') {
                setReactions(prev => ({ ...prev, [emoji]: Math.max(0, (prev[emoji] || 1) - 2) })); // Compensate optimistic
            }
        } catch (err) { }
    };

    return (
        <div className={`post-card ${isFirst ? 'post-card-first' : ''}`} id={`post-${id}`}>
            <div className="post-author">
                <div className="post-avatar">
                    {createdBy.username[0].toUpperCase()}
                </div>
                <div className="post-author-info">
                    <span className="post-username">{createdBy.username}</span>
                    {createdBy.badges && createdBy.badges.length > 0 && (
                        <div style={{ display: 'flex', gap: '4px', marginTop: '2px' }}>
                            {createdBy.badges.map(b => (
                                <span key={b} style={{ fontSize: '0.65rem', background: 'var(--accent)', color: 'white', padding: '1px 4px', borderRadius: '4px' }}>
                                    {b}
                                </span>
                            ))}
                        </div>
                    )}
                    <span className="post-date" style={{ marginTop: '2px' }}>
                        {new Date(createdAt).toLocaleDateString('en-US', {
                            year: 'numeric', month: 'short', day: 'numeric',
                            hour: '2-digit', minute: '2-digit',
                        })}
                    </span>
                </div>
            </div>
            <div className="post-content" style={{ marginTop: '12px', fontSize: '1rem', lineHeight: '1.6' }}>
                <MarkdownRenderer content={message} />
            </div>

            <div className="post-actions" style={{ display: 'flex', gap: '16px', marginTop: '16px', borderTop: '1px solid var(--border)', paddingTop: '12px', alignItems: 'center' }}>
                <div className="post-reactions" style={{ display: 'flex', gap: '8px' }}>
                    {Object.entries(reactions).filter(([_, count]) => count > 0).map(([emoji, count]) => (
                        <button key={emoji} onClick={() => handleReact(emoji)} style={{ background: 'var(--bg-card-hover)', border: '1px solid var(--border)', borderRadius: '16px', padding: '2px 8px', fontSize: '0.875rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--text-primary)' }}>
                            {emoji} <span>{count}</span>
                        </button>
                    ))}
                    <button
                        onClick={() => handleReact('👍')}
                        className="btn btn-ghost"
                        style={{ padding: '2px 8px', fontSize: '0.875rem', opacity: 0.7 }}
                        title="React 👍"
                    >
                        +👍
                    </button>
                    <button
                        onClick={() => handleReact('❤️')}
                        className="btn btn-ghost"
                        style={{ padding: '2px 8px', fontSize: '0.875rem', opacity: 0.7 }}
                        title="React ❤️"
                    >
                        +❤️
                    </button>
                </div>

                <div style={{ flex: 1 }}></div>

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

            {updatedAt && (
                <div className="post-edited">
                    Edited {new Date(updatedAt).toLocaleDateString()}
                </div>
            )}
        </div>
    );
}
