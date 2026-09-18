/**
 * Topic page — server-rendered. Posts and the reply box live in one client island
 * because "Quote Reply" writes into the reply box.
 */
import { Suspense } from 'react';
import Link from 'next/link';
import AdBanner from '@/components/AdBanner';
import Conversation from '@/components/Conversation';
import Pagination from '@/components/Pagination';
import { fetchApi, fetchApiOr } from '@/lib/server-api';
import type { PostList, Topic } from '@/types';

export default async function TopicPage(props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
    const { id } = await props.params;
    const searchParams = await props.searchParams;
    const page = typeof searchParams.page === 'string' ? searchParams.page : '1';

    const [topic, posts, similar] = await Promise.all([
        fetchApi<Topic>(`/api/topics/${id}`),
        fetchApi<PostList>(`/api/posts/topic/${id}?page=${page}`),
        fetchApiOr<Topic[]>(`/api/topics/${id}/similar`, [], 60),  // suggestions can lag
    ]);

    return (
        <div className="container">
            <ol className="breadcrumb">
                <li><Link href="/">Boards</Link></li>
                <li><Link href={`/boards/${topic.board_id}`}>{topic.board_name}</Link></li>
                <li>{topic.subject}</li>
            </ol>

            <div className="content-grid">
                <div>
                    <div className="page-header" style={{ paddingTop: 0 }}>
                        <h1 className="page-title">
                            {topic.is_pinned && <span className="topic-pinned">📌 </span>}
                            {topic.is_locked && <span className="topic-locked">🔒 </span>}
                            {topic.subject}
                        </h1>
                        <div style={{ display: 'flex', gap: 16, color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: 8 }}>
                            <span>Started by <strong style={{ color: 'var(--text-secondary)' }}>{topic.starter.username}</strong></span>
                            <span>{topic.views_count} views</span>
                            <span>{topic.replies_count} replies</span>
                        </div>
                    </div>

                    <Conversation topicId={topic.id} isLocked={topic.is_locked} posts={posts.results} />

                    <Suspense>
                        <Pagination currentPage={parseInt(page)} totalPages={posts.total_pages} />
                    </Suspense>

                    {similar.length > 0 && (
                        <div className="similar-topics" style={{ marginTop: 32, padding: 24, background: 'var(--bg-card-hover)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)' }}>
                            <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 16 }}>
                                You might also like
                            </h3>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
                                {similar.map(st => (
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
                </div>

                <aside>
                    <div className="form-card" style={{ marginTop: 112 }}>
                        <h3 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 8, color: 'var(--text-primary)' }}>
                            Topic Info
                        </h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            <div>Started by: <strong>{topic.starter.username}</strong></div>
                            <div>Views: <strong>{topic.views_count}</strong></div>
                            <div>Replies: <strong>{topic.replies_count}</strong></div>
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
