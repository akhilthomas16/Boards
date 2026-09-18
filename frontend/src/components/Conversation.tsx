/**
 * The posts of a topic plus the reply box. One island: "Quote Reply" on a post writes into the box.
 */
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import MarkdownEditor from './MarkdownEditor';
import PostCard from './PostCard';
import api from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { Post } from '@/types';

interface ConversationProps {
    topicId: number;
    isLocked: boolean;
    posts: Post[];
}

export default function Conversation({ topicId, isLocked, posts }: ConversationProps) {
    const router = useRouter();
    const { user } = useAuth();
    const [replyMessage, setReplyMessage] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [aiLoading, setAiLoading] = useState(false);
    const [error, setError] = useState('');
    const [myReactions, setMyReactions] = useState<Record<number, string[]>>({});

    // Server-rendered pages carry no cookie, so which reactions are mine is asked for here.
    useEffect(() => {
        if (!user) {
            setMyReactions({});
            return;
        }
        api.get<Record<number, string[]>>(`/api/posts/topic/${topicId}/my-reactions`)
            .then(setMyReactions)
            .catch(() => {});
    }, [user, topicId, posts]);

    const quote = (username: string, text: string) =>
        setReplyMessage(prev => `${prev}\n\n> **${username}** wrote:\n> ${text.split('\n').join('\n> ')}\n\n`);

    const handleReply = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!replyMessage.trim()) return;
        setSubmitting(true);
        setError('');

        try {
            await api.post<Post>(`/api/posts/topic/${topicId}`, { message: replyMessage });
            setReplyMessage('');
            router.refresh();  // the server page re-renders with the new post
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed to post reply');
        } finally {
            setSubmitting(false);
        }
    };

    const handleAiSuggest = async () => {
        setAiLoading(true);
        try {
            const response = await api.post<{ generated_text: string }>(
                `/api/content/suggest-reply?topic_id=${topicId}`,
                {}
            );
            setReplyMessage(response.generated_text);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'AI suggestion failed');
        } finally {
            setAiLoading(false);
        }
    };

    return (
        <>
            {error && <div className="alert alert-error">{error}</div>}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {posts.map((post, index) => (
                    <PostCard
                        key={post.id}
                        post={post}
                        myReactions={myReactions[post.id] ?? []}
                        isFirst={index === 0}
                        onQuote={user ? (text) => quote(post.created_by.username, text) : undefined}
                        onChanged={() => router.refresh()}
                    />
                ))}
            </div>

            {user && !isLocked && (
                <div className="form-card fade-in" style={{ marginTop: 24 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                        <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Post a Reply</h3>
                        <button className="ai-button" onClick={handleAiSuggest} disabled={aiLoading}>
                            <span className="sparkle">✨</span>
                            {aiLoading ? 'Thinking...' : 'AI Suggest'}
                        </button>
                    </div>
                    <form onSubmit={handleReply}>
                        <div className="form-group">
                            <MarkdownEditor
                                ariaLabel="Reply"
                                value={replyMessage}
                                onChange={setReplyMessage}
                                placeholder="Write your reply using markdown..."
                            />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                            <button type="submit" className="btn btn-primary" disabled={submitting}>
                                {submitting ? 'Posting...' : 'Post Reply'}
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {isLocked && (
                <div className="alert" style={{ background: 'var(--bg-glass)', border: '1px solid var(--border)', marginTop: 24, textAlign: 'center' }}>
                    🔒 This topic is locked. No new replies can be posted.
                </div>
            )}
        </>
    );
}
