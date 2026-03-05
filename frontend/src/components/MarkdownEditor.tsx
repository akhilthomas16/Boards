/**
 * Markdown Editor with preview tab and image upload support (drag & drop, paste).
 */
'use client';

import { useState, useRef, useEffect } from 'react';
import MarkdownRenderer from './MarkdownRenderer';
import { getTokens } from '@/lib/api';

interface UserMention {
    username: string;
    avatar_url: string | null;
}

interface MarkdownEditorProps {
    value: string;
    onChange: (val: string) => void;
    placeholder?: string;
    maxLength?: number;
}

export default function MarkdownEditor({
    value,
    onChange,
    placeholder = 'Write your message... (You can drag & drop or paste images)',
    maxLength = 4000,
}: MarkdownEditorProps) {
    const [tab, setTab] = useState<'write' | 'preview'>('write');
    const [isUploading, setIsUploading] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Mention state
    const [mentionQuery, setMentionQuery] = useState<{ query: string, index: number } | null>(null);
    const [mentionUsers, setMentionUsers] = useState<UserMention[]>([]);
    const [mentionIndex, setMentionIndex] = useState(0);

    useEffect(() => {
        if (!mentionQuery) {
            setMentionUsers([]);
            return;
        }
        const fetchUsers = async () => {
            try {
                const url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
                const res = await fetch(`${url}/api/profiles/search/users?q=${mentionQuery.query}`);
                if (res.ok) {
                    const data = await res.json();
                    setMentionUsers(data);
                    setMentionIndex(0);
                }
            } catch (err) { }
        };
        const timeout = setTimeout(fetchUsers, 200);
        return () => clearTimeout(timeout);
    }, [mentionQuery]);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (mentionUsers.length > 0 && mentionQuery) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setMentionIndex((mentionIndex + 1) % mentionUsers.length);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setMentionIndex((mentionIndex - 1 + mentionUsers.length) % mentionUsers.length);
            } else if (e.key === 'Enter' || e.key === 'Tab') {
                e.preventDefault();
                insertMention(mentionUsers[mentionIndex].username);
            } else if (e.key === 'Escape') {
                setMentionQuery(null);
            }
        }
    };

    const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const val = e.target.value;
        onChange(val);

        const cursor = e.target.selectionStart;
        const textBeforeCursor = val.substring(0, cursor);
        const match = textBeforeCursor.match(/(?:^|\s)@(\w*)$/);

        if (match) {
            setMentionQuery({ query: match[1], index: cursor - match[1].length });
        } else {
            setMentionQuery(null);
        }
    };

    const insertMention = (username: string) => {
        if (!mentionQuery || !textareaRef.current) return;
        const start = mentionQuery.index;
        const before = value.substring(0, start);
        const after = value.substring(textareaRef.current.selectionStart);
        const newText = `${before}${username} ${after}`;
        onChange(newText);
        setMentionQuery(null);

        setTimeout(() => {
            if (textareaRef.current) {
                textareaRef.current.selectionStart = textareaRef.current.selectionEnd = start + username.length + 1;
                textareaRef.current.focus();
            }
        }, 0);
    };

    const insertText = (text: string) => {
        const textarea = textareaRef.current;
        if (!textarea) {
            onChange(value + text);
            return;
        }

        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const newValue = value.substring(0, start) + text + value.substring(end);
        onChange(newValue);

        setTimeout(() => {
            textarea.selectionStart = textarea.selectionEnd = start + text.length;
            textarea.focus();
        }, 0);
    };

    const uploadImage = async (file: File) => {
        setIsUploading(true);
        const tokens = getTokens();
        const formData = new FormData();
        formData.append('file', file);

        try {
            const url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
            const res = await fetch(`${url}/api/upload/image`, {
                method: 'POST',
                headers: tokens ? { Authorization: `Bearer ${tokens.access}` } : {},
                body: formData,
            });

            if (res.ok) {
                const data = await res.json();
                insertText(`![${file.name}](${data.url})\n`);
            } else {
                const errData = await res.json();
                alert(`Upload failed: ${errData.detail || 'Unknown error'}`);
            }
        } catch (err) {
            console.error('Image upload failed:', err);
            alert('Failed to connect to the upload server.');
        } finally {
            setIsUploading(false);
        }
    };

    const handleDrop = async (e: React.DragEvent) => {
        e.preventDefault();
        const file = e.dataTransfer.files?.[0];
        if (file && file.type.startsWith('image/')) {
            await uploadImage(file);
        }
    };

    const handlePaste = async (e: React.ClipboardEvent) => {
        const file = e.clipboardData.files?.[0];
        if (file && file.type.startsWith('image/')) {
            e.preventDefault();
            await uploadImage(file);
        }
    };

    return (
        <div className="markdown-editor" style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden', position: 'relative' }}>
            <div className="editor-tabs" style={{ display: 'flex', background: 'var(--bg-card-hover)', borderBottom: '1px solid var(--border)' }}>
                <button
                    type="button"
                    className={`tab-btn ${tab === 'write' ? 'active' : ''}`}
                    onClick={() => setTab('write')}
                    style={{ padding: '8px 16px', background: tab === 'write' ? 'transparent' : 'rgba(0,0,0,0.2)', color: tab === 'write' ? 'var(--text-primary)' : 'var(--text-muted)', border: 'none', cursor: 'pointer', borderBottom: tab === 'write' ? '2px solid var(--accent)' : '2px solid transparent' }}
                >
                    Write
                </button>
                <button
                    type="button"
                    className={`tab-btn ${tab === 'preview' ? 'active' : ''}`}
                    onClick={() => setTab('preview')}
                    style={{ padding: '8px 16px', background: tab === 'preview' ? 'transparent' : 'rgba(0,0,0,0.2)', color: tab === 'preview' ? 'var(--text-primary)' : 'var(--text-muted)', border: 'none', cursor: 'pointer', borderBottom: tab === 'preview' ? '2px solid var(--accent)' : '2px solid transparent' }}
                >
                    Preview
                </button>
            </div>

            {isUploading && (
                <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10 }}>
                    <div style={{ background: 'var(--bg-card)', padding: '16px 24px', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div className="spinner" style={{ width: '20px', height: '20px', border: '2px solid var(--accent)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
                        <span>Uploading image...</span>
                    </div>
                </div>
            )}

            <div className="editor-content" style={{ padding: '12px' }}>
                {tab === 'write' ? (
                    <div style={{ position: 'relative' }}>
                        <textarea
                            ref={textareaRef}
                            className="form-textarea"
                            value={value}
                            onChange={handleTextChange}
                            onKeyDown={handleKeyDown}
                            onDrop={handleDrop}
                            onDragOver={(e) => e.preventDefault()}
                            onPaste={handlePaste}
                            placeholder={placeholder}
                            maxLength={maxLength}
                            rows={5}
                            style={{ border: 'none', padding: 0, outline: 'none', background: 'transparent', boxShadow: 'none', width: '100%', resize: 'vertical', minHeight: '120px' }}
                        />
                        {mentionUsers.length > 0 && mentionQuery && (
                            <div className="mention-dropdown" style={{ position: 'absolute', bottom: '100%', left: 0, background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', zIndex: 50, minWidth: '200px', overflow: 'hidden' }}>
                                {mentionUsers.map((u, i) => (
                                    <button
                                        key={u.username}
                                        type="button"
                                        onClick={() => insertMention(u.username)}
                                        style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', width: '100%', textAlign: 'left', background: i === mentionIndex ? 'var(--bg-card-hover)' : 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-primary)' }}
                                    >
                                        <div style={{ width: 24, height: 24, borderRadius: '50%', background: 'var(--accent)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px' }}>
                                            {u.username[0].toUpperCase()}
                                        </div>
                                        {u.username}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                ) : (
                    <div style={{ minHeight: '130px', padding: '8px 0' }}>
                        {value ? <MarkdownRenderer content={value} /> : <p style={{ color: 'var(--text-muted)' }}>Nothing to preview</p>}
                    </div>
                )}
            </div>
        </div>
    );
}
