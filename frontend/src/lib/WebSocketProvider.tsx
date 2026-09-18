'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import api, { API_BASE } from './api';
import { useAuth } from './auth';

export interface Notification {
    id: number;
    message: string;
    link: string;
    actor: string;
    is_read: boolean;
    created_at: string;
}

interface WebSocketContextType {
    notifications: Notification[];
    unreadCount: number;
    markAsRead: (id: number) => Promise<void>;
    markAllAsRead: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export function WebSocketProvider({ children }: { children: ReactNode }) {
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const unreadCount = notifications.filter(n => !n.is_read).length;
    const { user } = useAuth();

    useEffect(() => {
        if (!user) return;

        // Fetch initial notifications
        api.get<Notification[]>('/api/notifications/')
            .then(setNotifications)
            .catch(console.error);

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
                    const newNotif = JSON.parse(event.data);
                    setNotifications(prev => [newNotif, ...prev]);
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
        };
    }, [user]);

    const markAsRead = async (id: number) => {
        try {
            setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));

            await api.post(`/api/notifications/${id}/read`, {});
        } catch (error) {
            console.error('Failed to mark notification as read', error);
        }
    };

    const markAllAsRead = () => {
        notifications.filter(n => !n.is_read).forEach(n => markAsRead(n.id));
    };

    return (
        <WebSocketContext.Provider value={{ notifications, unreadCount, markAsRead, markAllAsRead }}>
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
