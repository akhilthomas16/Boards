/**
 * Search page — server-rendered from ?q=. The form is a plain GET, so it needs no client code.
 */
import Link from 'next/link';
import { fetchApi } from '@/lib/server-api';
import type { SearchResponse } from '@/types';

export default async function SearchPage(props: {
    searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
    const searchParams = await props.searchParams;
    const query = typeof searchParams.q === 'string' ? searchParams.q.trim() : '';
    const found = query.length >= 2
        ? await fetchApi<SearchResponse>(`/api/search/?q=${encodeURIComponent(query)}`)
        : null;

    return (
        <div className="container">
            <div className="page-header">
                <h1 className="page-title">Search</h1>
            </div>

            <form action="/search" method="GET" style={{ marginBottom: 32 }}>
                <div style={{ display: 'flex', gap: 12 }}>
                    <label className="sr-only" htmlFor="search-q">Search</label>
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
                </>
            ) : (
                <div className="form-card" style={{ textAlign: 'center', padding: 40 }}>
                    <p style={{ color: 'var(--text-secondary)' }}>Enter a search query to find boards, topics, and posts</p>
                </div>
            )}
        </div>
    );
}
