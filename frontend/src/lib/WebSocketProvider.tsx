'use client';

import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from 'react';
import api, { API_BASE } from './api';
import { useAuth } from './auth';
import type { Notification } from '@/types';

export type { Notification };

interface NotificationPage {
    count: number;
    results: Notification[];
}

interface WebSocketContextType {
    notifications: Notification[];  // the most recent few, for the navbar dropdown
    unreadCount: number;
    markAsRead: (id: number) => Promise<void>;
    markAllAsRead: () => Promise<void>;
    refreshUnread: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);
const RECENT = 10;

export function WebSocketProvider({ children }: { children: ReactNode }) {
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const { user } = useAuth();

    // The badge comes from the API, not from counting the loaded page.
    const refreshUnread = useCallback(() => {
        api.get<{ unread: number }>('/api/notifications/unread-count')
            .then(({ unread }) => setUnreadCount(unread))
            .catch(() => {});
    }, []);

    useEffect(() => {
        if (!user) return;

        api.get<NotificationPage>(`/api/notifications/?page_size=${RECENT}`)
            .then((page) => setNotifications(page.results))
            .catch(console.error);
        refreshUnread();

        // The access cookie authenticates the handshake. Reconnect with backoff (1s, 2s, 4s … 30s)
        // after an API restart or network drop; `cancelled` stops it on logout or unmount.
        let ws: WebSocket;
        let cancelled = false;
        let retries = 0;
        let retryTimer: ReturnType<typeof setTimeout>;

        const connect = () => {
            ws = new WebSocket(API_BASE.replace(/^http/, 'ws') + '/api/notifications/ws');
            ws.onopen = () => { retries = 0; };
            ws.onmessage = (event) => {
                try {
                    const incoming = JSON.parse(event.data) as Notification;
                    setNotifications(prev => [incoming, ...prev].slice(0, RECENT));
                    setUnreadCount(prev => prev + 1);
                } catch (err) {
                    console.error('Failed to parse WebSocket message', err);
                }
            };
            ws.onclose = () => {
                if (cancelled) return;
                retryTimer = setTimeout(connect, Math.min(30000, 1000 * 2 ** retries++));
            };
        };
        connect();

        return () => {
            cancelled = true;
            clearTimeout(retryTimer);
            ws.close();
            setNotifications([]);
            setUnreadCount(0);
        };
    }, [user, refreshUnread]);

    const markAsRead = async (id: number) => {
        setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
        setUnreadCount(prev => Math.max(0, prev - 1));
        try {
            await api.post(`/api/notifications/${id}/read`, {});
        } catch (error) {
            console.error('Failed to mark notification as read', error);
            refreshUnread();
        }
    };

    const markAllAsRead = async () => {
        // One request; this used to be one request per unread notification.
        setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
        setUnreadCount(0);
        try {
            await api.post('/api/notifications/read-all', {});
        } catch (error) {
            console.error('Failed to mark notifications read', error);
            refreshUnread();
        }
    };

    return (
        <WebSocketContext.Provider value={{ notifications, unreadCount, markAsRead, markAllAsRead, refreshUnread }}>
            {children}
        </WebSocketContext.Provider>
    );
}

export function useWebSockets() {
    const context = useContext(WebSocketContext);
    if (!context) {
        throw new Error('useWebSockets must be used within a WebSocketProvider');
    }
    return context;
}
