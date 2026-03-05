'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { getTokens } from './api';

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

    useEffect(() => {
        // Fetch initial notifications
        const tokens = getTokens();
        if (!tokens) return;

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

        fetch(`${apiUrl}/api/notifications/`, {
            headers: { Authorization: `Bearer ${tokens.access}` }
        })
            .then(res => res.json())
            .then(data => {
                if (Array.isArray(data)) setNotifications(data);
            })
            .catch(console.error);

        // Setup WebSocket connection
        const wsUrl = apiUrl.replace('http', 'ws') + `/api/notifications/ws?token=${tokens.access}`;
        const ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
            try {
                const newNotif = JSON.parse(event.data);
                setNotifications(prev => [newNotif, ...prev]);

                // Optionally play a soft sound or show browser notification
                if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
                    new Notification('Boards Forum', { body: `${newNotif.actor} ${newNotif.message}` });
                }
            } catch (err) {
                console.error('Failed to parse WebSocket message', err);
            }
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
        };

        return () => {
            ws.close();
        };
    }, []);

    const markAsRead = async (id: number) => {
        try {
            setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));

            const tokens = getTokens();
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
            await fetch(`${apiUrl}/api/notifications/${id}/read`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${tokens?.access}` }
            });
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
