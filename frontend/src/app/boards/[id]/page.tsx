/**
 * Board topics page — list topics with HTMX new topic form.
 */
'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import { useAuth } from '@/lib/auth';
import AdBanner from '@/components/AdBanner';
import Pagination from '@/components/Pagination';
import MarkdownEditor from '@/components/MarkdownEditor';

interface Topic {
    id: number;
    subject: string;
    slug: string;
    starter: { id: number; username: string };
    views_count: number;
    replies_count: number;
    is_pinned: boolean;
    is_locked: boolean;
    last_updated: string;
}

interface Board {
    id: number;
    name: string;
    slug: string;
    description: string;
}

interface TopicsResponse {
    count: number;
    page: number;
    total_pages: number;
    results: Topic[];
}

export default function BoardTopicsPage() {
    const params = useParams();
    const boardId = params.id as string;
    const searchParams = useSearchParams();
    const page = searchParams.get('page') || '1';
    const { user } = useAuth();

    const [board, setBoard] = useState<Board | null>(null);
    const [topics, setTopics] = useState<Topic[]>([]);
    const [loading, setLoading] = useState(true);
    const [totalPages, setTotalPages] = useState(1);
    const [showForm, setShowForm] = useState(false);
    const [formSubject, setFormSubject] = useState('');
    const [formTags, setFormTags] = useState('');
    const [formMessage, setFormMessage] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');
    const tableRef = useRef<HTMLTableSectionElement>(null);

    useEffect(() => {
        Promise.all([
            api.get<Board>(`/api/boards/${boardId}`),
            api.get<TopicsResponse>(`/api/topics/board/${boardId}?page=${page}`),
        ])
            .then(([boardData, topicsData]) => {
                setBoard(boardData);
                setTopics(topicsData.results);
                setTotalPages(topicsData.total_pages);
            })
            .catch((err) => setError(err.message))
            .finally(() => setLoading(false));
    }, [boardId]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formSubject.trim() || !formMessage.trim()) return;
        setSubmitting(true);

        try {
            const newTopic = await api.post<Topic>(`/api/topics/board/${boardId}`, {
                subject: formSubject,
                message: formMessage,
                tags: formTags,
            });
            setTopics([newTopic, ...topics]);
            setFormSubject('');
            setFormTags('');
            setFormMessage('');
            setShowForm(false);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed to create topic');
        } finally {
            setSubmitting(false);
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
                <li>{board?.name}</li>
            </ol>

            <div className="content-grid">
                <div>
                    <div className="page-header" style={{ paddingTop: 0 }}>
                        <h1 className="page-title">{board?.name}</h1>
                        <p className="page-subtitle">{board?.description}</p>
                    </div>

                    {/* Actions */}
                    <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
                        {user && (
                            <button
                                className="btn btn-primary"
                                onClick={() => setShowForm(!showForm)}
                            >
                                {showForm ? 'Cancel' : '+ New Topic'}
                            </button>
                        )}
                    </div>

                    {error && <div className="alert alert-error">{error}</div>}

                    {/* HTMX-style New Topic Form */}
                    {showForm && (
                        <div className="form-card fade-in" style={{ marginBottom: 24 }}>
                            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 20 }}>
                                Start a New Topic
                            </h3>
                            <form onSubmit={handleSubmit}>
                                <div className="form-group">
                                    <label className="form-label">Subject</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        value={formSubject}
                                        onChange={(e) => setFormSubject(e.target.value)}
                                        placeholder="What would you like to discuss?"
                                        required
                                        maxLength={255}
                                    />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Tags (Optional)</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        value={formTags}
                                        onChange={(e) => setFormTags(e.target.value)}
                                        placeholder="e.g. bug, discussion, help (comma separated)"
                                        maxLength={200}
                                    />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Message</label>
                                    <MarkdownEditor
                                        value={formMessage}
                                        onChange={setFormMessage}
                                        placeholder="Share your thoughts using markdown..."
                                    />
                                </div>
                                <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                                    <button
                                        type="button"
                                        className="btn btn-ghost"
                                        onClick={() => setShowForm(false)}
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        className="btn btn-success"
                                        disabled={submitting}
                                    >
                                        {submitting ? 'Posting...' : 'Post Topic'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    <AdBanner
                        slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_BANNER || 'banner'}
                        className="ad-infeed"
                    />

                    {/* Topic Table */}
                    {topics.length === 0 ? (
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
                            <tbody ref={tableRef}>
                                {topics.map((topic) => (
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

                    <Pagination currentPage={parseInt(page)} totalPages={totalPages} />
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
