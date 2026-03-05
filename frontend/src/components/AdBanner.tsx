/**
 * Google AdSense banner component.
 * Supports different ad slots: banner, sidebar, infeed.
 */
'use client';

import { useEffect, useRef } from 'react';

interface AdBannerProps {
    slot: string;
    format?: 'auto' | 'rectangle' | 'horizontal' | 'vertical';
    className?: string;
}

export default function AdBanner({ slot, format = 'auto', className = '' }: AdBannerProps) {
    const adRef = useRef<HTMLModElement>(null);

    useEffect(() => {
        try {
            // @ts-expect-error — Google AdSense global
            (window.adsbygoogle = window.adsbygoogle || []).push({});
        } catch {
            // AdSense not loaded (dev mode or blocked)
        }
    }, []);

    const clientId = process.env.NEXT_PUBLIC_ADSENSE_CLIENT_ID || '';

    if (!clientId) {
        // Dev placeholder
        return (
            <div className={`ad-placeholder ${className}`}>
                <div className="ad-placeholder-inner">
                    <span className="ad-label">Advertisement</span>
                    <span className="ad-debug">AdSense Slot: {slot}</span>
                </div>
            </div>
        );
    }

    return (
        <div className={`ad-container ${className}`}>
            <ins
                className="adsbygoogle"
                ref={adRef}
                style={{ display: 'block' }}
                data-ad-client={clientId}
                data-ad-slot={slot}
                data-ad-format={format}
                data-full-width-responsive="true"
            />
        </div>
    );
}
