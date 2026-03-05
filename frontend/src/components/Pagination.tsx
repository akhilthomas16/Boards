/**
 * Pagination component for Next.js app 
 */
"use client";
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';

interface PaginationProps {
    currentPage: number;
    totalPages: number;
}

export default function Pagination({ currentPage, totalPages }: PaginationProps) {
    const pathname = usePathname();
    const searchParams = useSearchParams();

    if (totalPages <= 1) return null;

    const createPageURL = (pageNumber: number) => {
        const params = new URLSearchParams(searchParams.toString());
        params.set('page', pageNumber.toString());
        return `${pathname}?${params.toString()}`;
    };

    // Build page numbers to display
    const pages = [];
    const maxVisiblePages = 5;

    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = startPage + maxVisiblePages - 1;

    if (endPage > totalPages) {
        endPage = totalPages;
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
        pages.push(i);
    }

    return (
        <div className="pagination" style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 32 }}>
            <Link
                href={createPageURL(Math.max(1, currentPage - 1))}
                className={`btn btn-ghost btn-sm ${currentPage === 1 ? 'disabled' : ''}`}
                style={{ pointerEvents: currentPage === 1 ? 'none' : 'auto', opacity: currentPage === 1 ? 0.5 : 1 }}
            >
                Previous
            </Link>

            {startPage > 1 && (
                <>
                    <Link href={createPageURL(1)} className="btn btn-ghost btn-sm">1</Link>
                    {startPage > 2 && <span style={{ padding: '4px 8px', color: 'var(--text-muted)' }}>...</span>}
                </>
            )}

            {pages.map(page => (
                <Link
                    key={page}
                    href={createPageURL(page)}
                    className={`btn btn-sm ${page === currentPage ? 'btn-primary' : 'btn-ghost'}`}
                >
                    {page}
                </Link>
            ))}

            {endPage < totalPages && (
                <>
                    {endPage < totalPages - 1 && <span style={{ padding: '4px 8px', color: 'var(--text-muted)' }}>...</span>}
                    <Link href={createPageURL(totalPages)} className="btn btn-ghost btn-sm">{totalPages}</Link>
                </>
            )}

            <Link
                href={createPageURL(Math.min(totalPages, currentPage + 1))}
                className={`btn btn-ghost btn-sm ${currentPage === totalPages ? 'disabled' : ''}`}
                style={{ pointerEvents: currentPage === totalPages ? 'none' : 'auto', opacity: currentPage === totalPages ? 0.5 : 1 }}
            >
                Next
            </Link>
        </div>
    );
}
