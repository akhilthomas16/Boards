/**
 * Global Not Found Page
 */
import Link from 'next/link';

export default function NotFound() {
    return (
        <div className="container" style={{ minHeight: '60vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
            <h1 className="page-title" style={{ fontSize: '4rem', color: 'var(--accent)', marginBottom: 16 }}>404</h1>
            <h2 style={{ fontSize: '1.5rem', marginBottom: 24, color: 'var(--text-primary)' }}>Page Not Found</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 32, maxWidth: 500 }}>
                The page you are looking for might have been removed, had its name changed, or is temporarily unavailable.
            </p>
            <Link href="/" className="btn btn-primary">
                Return to Home
            </Link>
        </div>
    );
}
