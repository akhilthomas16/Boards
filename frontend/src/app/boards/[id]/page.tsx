/**
 * Board topics page — server-rendered. The new-topic form is the only client island.
 */
import { Suspense } from 'react';
import Link from 'next/link';
import AdBanner from '@/components/AdBanner';
import NewTopicForm from '@/components/NewTopicForm';
import Pagination from '@/components/Pagination';
import { fetchApi } from '@/lib/server-api';
import type { Board, TopicList } from '@/types';

export default async function BoardTopicsPage(props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
    const { id } = await props.params;
    const searchParams = await props.searchParams;
    const page = typeof searchParams.page === 'string' ? searchParams.page : '1';

    const [board, topics] = await Promise.all([
        fetchApi<Board>(`/api/boards/${id}`),
        fetchApi<TopicList>(`/api/topics/board/${id}?page=${page}`),
    ]);

    return (
        <div className="container">
            <ol className="breadcrumb">
                <li><Link href="/">Boards</Link></li>
                <li>{board.name}</li>
            </ol>

            <div className="content-grid">
                <div>
                    <div className="page-header" style={{ paddingTop: 0 }}>
                        <h1 className="page-title">{board.name}</h1>
                        <p className="page-subtitle">{board.description}</p>
                    </div>

                    <NewTopicForm boardId={board.id} />

                    <AdBanner
                        slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_BANNER || 'banner'}
                        className="ad-infeed"
                    />

                    {topics.results.length === 0 ? (
                        <div className="form-card" style={{ textAlign: 'center', padding: 40 }}>
                            <p style={{ color: 'var(--text-secondary)' }}>No topics yet — be the first to start a discussion!</p>
                        </div>
                    ) : (
                        <table className="topic-table">
                            <thead>
                                <tr>
                                    <th>Topic</th>
                                    <th>Starter</th>
                                    <th>Replies</th>
                                    <th>Views</th>
                                    <th>Last Update</th>
                                </tr>
                            </thead>
                            <tbody>
                                {topics.results.map((topic) => (
                                    <tr key={topic.id} className="fade-in">
                                        <td>
                                            <Link href={`/topics/${topic.id}`} className="topic-link">
                                                {topic.is_pinned && <span className="topic-pinned">📌 </span>}
                                                {topic.is_locked && <span className="topic-locked">🔒 </span>}
                                                {topic.subject}
                                            </Link>
                                        </td>
                                        <td style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                                            {topic.starter.username}
                                        </td>
                                        <td style={{ color: 'var(--text-secondary)' }}>{topic.replies_count}</td>
                                        <td style={{ color: 'var(--text-secondary)' }}>{topic.views_count}</td>
                                        <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                                            {new Date(topic.last_updated).toLocaleDateString()}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}

                    <Suspense>
                        <Pagination currentPage={parseInt(page)} totalPages={topics.total_pages} />
                    </Suspense>
                </div>

                <aside>
                    <AdBanner
                        slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_SIDEBAR || 'sidebar'}
                        className="ad-sidebar"
                    />
                </aside>
            </div>
        </div>
    );
}
