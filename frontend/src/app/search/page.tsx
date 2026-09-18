/**
 * Search page — server-rendered from ?q=. The form is a plain GET, so it needs no client code.
 */
import { Suspense } from 'react';
import Link from 'next/link';
import Pagination from '@/components/Pagination';
import { fetchApi } from '@/lib/server-api';
import type { SearchResponse } from '@/types';

const TYPES = ['all', 'board', 'topic', 'post'] as const;
type SearchType = typeof TYPES[number];
const PAGE_SIZE = 20;

export default async function SearchPage(props: {
    searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
    const searchParams = await props.searchParams;
    const query = typeof searchParams.q === 'string' ? searchParams.q.trim() : '';
    const type = (TYPES as readonly string[]).includes(String(searchParams.type))
        ? (searchParams.type as SearchType) : 'all';
    const page = typeof searchParams.page === 'string' ? Math.max(1, parseInt(searchParams.page) || 1) : 1;
    const found = query.length >= 2
        ? await fetchApi<SearchResponse>(
            `/api/search/?q=${encodeURIComponent(query)}&type=${type}&page=${page}&page_size=${PAGE_SIZE}`)
        : null;
    const totalPages = found ? Math.max(1, Math.ceil(found.total / PAGE_SIZE)) : 1;

    return (
        <div className="container">
            <div className="page-header">
                <h1 className="page-title">Search</h1>
            </div>

            <form action="/search" method="GET" style={{ marginBottom: 32 }}>
                <div style={{ display: 'flex', gap: 12 }}>
                    <label className="sr-only" htmlFor="search-q">Search</label>
                    <input type="hidden" name="type" value={type} />
                    <input
                        id="search-q"
                        type="text"
                        name="q"
                        className="form-input"
                        defaultValue={query}
                        placeholder="Search boards, topics, and posts..."
                        style={{ flex: 1 }}
                        minLength={2}
                        required
                    />
                    <button type="submit" className="btn btn-primary">
                        Search
                    </button>
                </div>
            </form>

            {found ? (
                <>
                    <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
                        {TYPES.map((tab) => {
                            const count = tab === 'all'
                                ? Object.values(found.counts).reduce((a, b) => a + b, 0)
                                : found.counts[tab];
                            return (
                                <Link
                                    key={tab}
                                    href={`/search?q=${encodeURIComponent(query)}&type=${tab}`}
                                    className={`btn btn-sm ${tab === type ? 'btn-primary' : 'btn-ghost'}`}
                                    aria-current={tab === type ? 'page' : undefined}
                                >
                                    {tab === 'all' ? 'All' : `${tab[0].toUpperCase()}${tab.slice(1)}s`}
                                    {count !== undefined && ` (${count})`}
                                </Link>
                            );
                        })}
                    </div>

                    <p style={{ color: 'var(--text-secondary)', marginBottom: 20, fontSize: '0.875rem' }}>
                        {found.total} result{found.total !== 1 ? 's' : ''} for &ldquo;<strong>{query}</strong>&rdquo;
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {found.results.map((result) => (
                            <Link href={result.url} key={`${result.type}-${result.id}`} className="search-result">
                                <span className="search-result-type">{result.type}</span>
                                <div className="search-result-title">{result.title}</div>
                                <div className="search-result-snippet">{result.snippet}</div>
                            </Link>
                        ))}
                    </div>
                    {found.results.length === 0 && (
                        <div className="form-card" style={{ textAlign: 'center', padding: 40 }}>
                            <p style={{ color: 'var(--text-secondary)' }}>No results found</p>
                        </div>
                    )}

                    <Suspense>
                        <Pagination currentPage={page} totalPages={totalPages} />
                    </Suspense>
                </>
            ) : (
                <div className="form-card" style={{ textAlign: 'center', padding: 40 }}>
                    <p style={{ color: 'var(--text-secondary)' }}>Enter a search query to find boards, topics, and posts</p>
                </div>
            )}
        </div>
    );
}
