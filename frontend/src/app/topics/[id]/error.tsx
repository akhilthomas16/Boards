'use client';

/** Segment-level boundary: a failed fetch here must not blow away the whole app shell. */
export default function SegmentError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
    return (
        <div className="container" style={{ paddingTop: 48 }}>
            <div className="alert alert-error" style={{ marginBottom: 24 }}>
                {error.message || 'Could not load this page.'}
            </div>
            <button className="btn btn-primary" onClick={reset}>Try again</button>
        </div>
    );
}
