/**
 * Start a new topic on a board. Client island: needs auth state and form state.
 */
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import MarkdownEditor from './MarkdownEditor';
import api from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { Topic } from '@/types';

export default function NewTopicForm({ boardId }: { boardId: number }) {
    const router = useRouter();
    const { user } = useAuth();
    const [open, setOpen] = useState(false);
    const [subject, setSubject] = useState('');
    const [tags, setTags] = useState('');
    const [message, setMessage] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');

    if (!user) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!subject.trim() || !message.trim()) return;
        setSubmitting(true);
        setError('');

        try {
            await api.post<Topic>(`/api/topics/board/${boardId}`, { subject, message, tags });
            setSubject('');
            setTags('');
            setMessage('');
            setOpen(false);
            router.refresh();  // re-render the server page with the new topic in place
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed to create topic');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <>
            <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
                <button className="btn btn-primary" onClick={() => setOpen(!open)} aria-expanded={open}>
                    {open ? 'Cancel' : '+ New Topic'}
                </button>
            </div>

            {error && <div className="alert alert-error">{error}</div>}

            {open && (
                <div className="form-card fade-in" style={{ marginBottom: 24 }}>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 20 }}>
                        Start a New Topic
                    </h3>
                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label className="form-label" htmlFor="topic-subject">Subject</label>
                            <input
                                id="topic-subject"
                                type="text"
                                className="form-input"
                                value={subject}
                                onChange={(e) => setSubject(e.target.value)}
                                placeholder="What would you like to discuss?"
                                required
                                maxLength={255}
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label" htmlFor="topic-tags">Tags (Optional)</label>
                            <input
                                id="topic-tags"
                                type="text"
                                className="form-input"
                                value={tags}
                                onChange={(e) => setTags(e.target.value)}
                                placeholder="e.g. bug, discussion, help (comma separated)"
                                maxLength={200}
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label" htmlFor="topic-message">Message</label>
                            <MarkdownEditor
                                id="topic-message"
                                value={message}
                                onChange={setMessage}
                                placeholder="Share your thoughts using markdown..."
                            />
                        </div>
                        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                            <button type="button" className="btn btn-ghost" onClick={() => setOpen(false)}>
                                Cancel
                            </button>
                            <button type="submit" className="btn btn-success" disabled={submitting}>
                                {submitting ? 'Posting...' : 'Post Topic'}
                            </button>
                        </div>
                    </form>
                </div>
            )}
        </>
    );
}
