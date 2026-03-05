/**
 * Topic page — view posts and reply with HTMX-style form and AI suggestions.
 */
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import { useAuth } from '@/lib/auth';
import PostCard from '@/components/PostCard';
import AdBanner from '@/components/AdBanner';
import Pagination from '@/components/Pagination';
import MarkdownEditor from '@/components/MarkdownEditor';

interface Post {
    id: number;
    message: string;
    topic_id: number;
    created_by: { id: number; username: string };
    updated_by: { id: number; username: string } | null;
    created_at: string;
    updated_at: string | null;
    reactions: Record<string, number>;
}

interface Topic {
    id: number;
    subject: string;
    board_id: number;
    board_name: string;
    starter: { id: number; username: string };
    views_count: number;
    replies_count: number;
    is_pinned: boolean;
    is_locked: boolean;
    tags: string;
}

interface SimilarTopic {
    id: number;
    subject: string;
    board_name: string;
}

interface PostsResponse {
    count: number;
    page: number;
    total_pages: number;
    results: Post[];
}

export default function TopicPage() {
    const params = useParams();
    const topicId = params.id as string;
    const searchParams = useSearchParams();
    const page = searchParams.get('page') || '1';
    const { user } = useAuth();

    const [topic, setTopic] = useState<Topic | null>(null);
    const [posts, setPosts] = useState<Post[]>([]);
    const [similarTopics, setSimilarTopics] = useState<SimilarTopic[]>([]);
    const [loading, setLoading] = useState(true);
    const [totalPages, setTotalPages] = useState(1);
    const [replyMessage, setReplyMessage] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [aiLoading, setAiLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        Promise.all([
            api.get<Topic>(`/api/topics/${topicId}`),
            api.get<PostsResponse>(`/api/posts/topic/${topicId}?page=${page}`),
            // We can gracefully handle failure for similar topics so it doesn't break the page
            api.get<SimilarTopic[]>(`/api/topics/${topicId}/similar`).catch(() => []),
        ])
            .then(([topicData, postsData, similarData]) => {
                setTopic(topicData);
                setPosts(postsData.results);
                setTotalPages(postsData.total_pages);
                setSimilarTopics(similarData || []);
            })
            .catch((err) => setError(err.message))
            .finally(() => setLoading(false));
    }, [topicId, page]);

    const handleReply = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!replyMessage.trim()) return;
        setSubmitting(true);

        try {
            const newPost = await api.post<Post>(`/api/posts/topic/${topicId}`, {
                message: replyMessage,
            });
            setPosts([...posts, newPost]);
            setReplyMessage('');
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

    if (loading) {
        return (
            <div className="container">
                <div className="loading-center"><div className="spinner"></div></div>
            </div>
        );
    }

    return (
        <div className="container">
            <ol className="breadcrumb">
                <li><Link href="/">Boards</Link></li>
                <li><Link href={`/boards/${topic?.board_id}`}>{topic?.board_name}</Link></li>
                <li>{topic?.subject}</li>
            </ol>

            <div className="content-grid">
                <div>
                    <div className="page-header" style={{ paddingTop: 0 }}>
                        <h1 className="page-title">
                            {topic?.is_pinned && <span className="topic-pinned">📌 </span>}
                            {topic?.is_locked && <span className="topic-locked">🔒 </span>}
                            {topic?.subject}
                        </h1>
                        <div style={{ display: 'flex', gap: 16, color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: 8 }}>
                            <span>Started by <strong style={{ color: 'var(--text-secondary)' }}>{topic?.starter.username}</strong></span>
                            <span>{topic?.views_count} views</span>
                            <span>{topic?.replies_count} replies</span>
                        </div>
                    </div>

                    {error && <div className="alert alert-error">{error}</div>}

                    {/* Posts */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        {posts.map((post, index) => (
                            <div key={post.id}>
                                <PostCard
                                    id={post.id}
                                    message={post.message}
                                    createdBy={post.created_by}
                                    createdAt={post.created_at}
                                    updatedAt={post.updated_at}
                                    isFirst={index === 0}
                                    initialReactions={post.reactions}
                                    onQuote={user ? (text) => setReplyMessage(prev => `${prev}\n\n> **${post.created_by.username}** wrote:\n> ${text.split('\\n').join('\\n> ')}\n\n`) : undefined}
                                />
                                {/* Inline ad every 5 posts */}
                                {index > 0 && index % 5 === 0 && (
                                    <AdBanner
                                        slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_INFEED || 'infeed'}
                                        className="ad-infeed"
                                    />
                                )}
                            </div>
                        ))}
                    </div>

                    <Pagination currentPage={parseInt(page)} totalPages={totalPages} />

                    {/* Similar Topics */}
                    {similarTopics.length > 0 && (
                        <div className="similar-topics" style={{ marginTop: 32, padding: 24, background: 'var(--bg-card-hover)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)' }}>
                            <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 16 }}>
                                You might also like
                            </h3>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
                                {similarTopics.map(st => (
                                    <Link key={st.id} href={`/topics/${st.id}`} className="similar-topic-card" style={{ padding: 16, background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', textDecoration: 'none', color: 'inherit', transition: 'transform 0.2s' }}>
                                        <div style={{ fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-primary)', marginBottom: 8, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                                            {st.subject}
                                        </div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                            in {st.board_name}
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Reply Form */}
                    {user && !topic?.is_locked && (
                        <div className="form-card fade-in" style={{ marginTop: 24 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                                <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Post a Reply</h3>
                                <button
                                    className="ai-button"
                                    onClick={handleAiSuggest}
                                    disabled={aiLoading}
                                >
                                    <span className="sparkle">✨</span>
                                    {aiLoading ? 'Thinking...' : 'AI Suggest'}
                                </button>
                            </div>
                            <form onSubmit={handleReply}>
                                <div className="form-group">
                                    <MarkdownEditor
                                        value={replyMessage}
                                        onChange={setReplyMessage}
                                        placeholder="Write your reply using markdown..."
                                    />
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                                    <button
                                        type="submit"
                                        className="btn btn-primary"
                                        disabled={submitting}
                                    >
                                        {submitting ? 'Posting...' : 'Post Reply'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    {topic?.is_locked && (
                        <div className="alert" style={{ background: 'var(--bg-glass)', border: '1px solid var(--border)', marginTop: 24, textAlign: 'center' }}>
                            🔒 This topic is locked. No new replies can be posted.
                        </div>
                    )}
                </div>

                <aside>
                    <div className="form-card" style={{ marginTop: 112 }}>
                        <h3 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 8, color: 'var(--text-primary)' }}>
                            Topic Info
                        </h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            <div>Started by: <strong>{topic?.starter.username}</strong></div>
                            <div>Views: <strong>{topic?.views_count}</strong></div>
                            <div>Replies: <strong>{topic?.replies_count}</strong></div>
                        </div>
                    </div>
                    <AdBanner
                        slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_SIDEBAR || 'sidebar'}
                        className="ad-sidebar"
                    />
                </aside>
            </div>
        </div>
    );
}
