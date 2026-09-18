/**
 * Home page — Board listing with premium glassmorphic cards (SSR).
 */
import BoardCard from '@/components/BoardCard';
import AdBanner from '@/components/AdBanner';
import Pagination from '@/components/Pagination';
import Link from 'next/link';
import { fetchApi, fetchApiOr } from '@/lib/server-api';
import type { Board, BoardList, Topic } from '@/types';

export default async function HomePage(props: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const searchParams = await props.searchParams;
  const page = typeof searchParams.page === 'string' ? searchParams.page : '1';

  let boards: Board[] = [];
  let trendingTopics: Topic[] = [];
  let totalPages = 1;
  let error = '';

  try {
    const [data, trending] = await Promise.all([
      fetchApi<BoardList>(`/api/boards/?page=${page}`, 60),  // the board list changes slowly
      fetchApiOr<Topic[]>('/api/topics/trending', [], 60),
    ]);
    boards = data.results;
    totalPages = data.total_pages;
    trendingTopics = trending;
  } catch (err: unknown) {
    error = err instanceof Error ? err.message : 'Failed to load boards';
  }

  return (
    <div className="container">
      <div className="content-grid">
        <div>
          <div className="page-header">
            <h1 className="page-title">Discussion Boards</h1>
            <p className="page-subtitle">
              Join the conversation — explore topics that interest you
            </p>
          </div>

          <AdBanner
            slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_BANNER || 'banner'}
            className="ad-banner-top"
          />

          {error ? (
            <div className="alert alert-error">{error}</div>
          ) : boards.length === 0 ? (
            <div className="form-card" style={{ textAlign: 'center', padding: 40 }}>
              <p style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>No boards yet</p>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                Create your first board via the admin panel
              </p>
            </div>
          ) : (
            <>
              <div className="boards-grid">
                {boards.map((board) => (
                  <BoardCard
                    key={board.id}
                    id={board.id}
                    name={board.name}
                    slug={board.slug}
                    description={board.description}
                    postsCount={board.posts_count}
                    topicsCount={board.topics_count}
                    lastPostAt={board.last_post_at}
                  />
                ))}
              </div>
              <Pagination currentPage={parseInt(page)} totalPages={totalPages} />
            </>
          )}
        </div>

        {/* Sidebar */}
        <aside>
          <div className="form-card" style={{ marginTop: 112, marginBottom: 24 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)' }}>
              Welcome to Hash Out
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 16 }}>
              A modern discussion platform for thoughtful conversations.
              Sign up to create topics and join the discussion.
            </p>
          </div>

          {trendingTopics.length > 0 && (
            <div className="form-card" style={{ marginBottom: 24 }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 16, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: 'var(--danger)' }}>🔥</span> Trending Topics
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {trendingTopics.map((topic) => (
                  <Link href={`/topics/${topic.id}`} key={topic.id} style={{ display: 'block', textDecoration: 'none', color: 'inherit' }}>
                    <div style={{ padding: '8px', borderRadius: 'var(--radius-md)', background: 'var(--bg-card-hover)', transition: 'background 0.2s', border: '1px solid var(--border)' }}>
                      <h4 style={{ fontSize: '0.9rem', fontWeight: 500, marginBottom: '6px', color: 'var(--accent)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {topic.subject}
                      </h4>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        <span>in {topic.board_name}</span>
                        <span>{topic.views_count} views</span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          <AdBanner
            slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_SIDEBAR || 'sidebar'}
            className="ad-sidebar"
          />
        </aside>
      </div>
    </div>
  );
}
