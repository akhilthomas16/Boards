/**
 * Board card component — glassmorphic card for board listings.
 */
import Link from 'next/link';

interface BoardCardProps {
    id: number;
    name: string;
    slug: string;
    description: string;
    postsCount: number;
    topicsCount: number;
    lastPostAt: string | null;
}

export default function BoardCard({
    id, name, slug, description, postsCount, topicsCount, lastPostAt,
}: BoardCardProps) {
    return (
        <Link href={`/boards/${id}`} className="board-card">
            <div className="board-card-inner">
                <div className="board-card-header">
                    <div className="board-icon">
                        {name[0].toUpperCase()}
                    </div>
                    <div className="board-info">
                        <h3 className="board-name">{name}</h3>
                        <p className="board-description">{description}</p>
                    </div>
                </div>
                <div className="board-stats">
                    <div className="stat">
                        <span className="stat-value">{topicsCount}</span>
                        <span className="stat-label">Topics</span>
                    </div>
                    <div className="stat">
                        <span className="stat-value">{postsCount}</span>
                        <span className="stat-label">Posts</span>
                    </div>
                    <div className="stat">
                        <span className="stat-label">
                            {lastPostAt
                                ? `Last: ${new Date(lastPostAt).toLocaleDateString()}`
                                : 'No posts yet'}
                        </span>
                    </div>
                </div>
            </div>
        </Link>
    );
}
