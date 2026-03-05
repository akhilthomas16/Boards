/**
 * Global Error Page
 */
'use client';

import { useEffect } from 'react';

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        // Log the error to an error reporting service like Sentry
        console.error(error);
    }, [error]);

    return (
        <div className="container" style={{ minHeight: '60vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
            <div className="alert alert-error" style={{ marginBottom: 32, maxWidth: 600 }}>
                <h2 style={{ fontSize: '1.25rem', marginBottom: 8 }}>Something went wrong!</h2>
                <p style={{ fontSize: '0.875rem', opacity: 0.9 }}>{error.message || 'An unexpected error occurred.'}</p>
            </div>
            <button
                className="btn btn-primary"
                onClick={() => reset()}
            >
                Try again
            </button>
        </div>
    );
}
