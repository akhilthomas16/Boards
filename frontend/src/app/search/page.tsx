/**
 * Search page — Elasticsearch-powered search with type filtering.
 */
'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';

interface SearchResult {
    type: string;
    id: number;
    title: string;
    snippet: string;
    url: string;
}

interface SearchResponse {
    query: string;
    total: number;
    results: SearchResult[];
}

function SearchResults() {
    const searchParams = useSearchParams();
    const query = searchParams.get('q') || '';
    const [results, setResults] = useState<SearchResult[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [searchInput, setSearchInput] = useState(query);

    useEffect(() => {
        if (query.length >= 2) {
            setLoading(true);
            api.get<SearchResponse>(`/api/search/?q=${encodeURIComponent(query)}`)
                .then((data) => {
                    setResults(data.results);
                    setTotal(data.total);
                })
                .catch(() => setResults([]))
                .finally(() => setLoading(false));
        }
    }, [query]);

    return (
        <div className="container">
            <div className="page-header">
                <h1 className="page-title">Search</h1>
            </div>

            <form action="/search" method="GET" style={{ marginBottom: 32 }}>
                <div style={{ display: 'flex', gap: 12 }}>
                    <input
                        type="text"
                        name="q"
                        className="form-input"
                        value={searchInput}
                        onChange={(e) => setSearchInput(e.target.value)}
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

            {loading ? (
                <div className="loading-center"><div className="spinner"></div></div>
            ) : query ? (
                <>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: 20, fontSize: '0.875rem' }}>
                        {total} result{total !== 1 ? 's' : ''} for &ldquo;<strong>{query}</strong>&rdquo;
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {results.map((result, i) => (
                            <Link href={result.url} key={`${result.type}-${result.id}-${i}`} className="search-result">
                                <span className="search-result-type">{result.type}</span>
                                <div className="search-result-title">{result.title}</div>
                                <div className="search-result-snippet">{result.snippet}</div>
                            </Link>
                        ))}
                    </div>
                    {results.length === 0 && (
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

export default function SearchPage() {
    return (
        <Suspense fallback={<div className="container"><div className="loading-center"><div className="spinner"></div></div></div>}>
            <SearchResults />
        </Suspense>
    );
}
