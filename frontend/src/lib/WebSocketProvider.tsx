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

        // The access cookie authenticates the handshake.
        const ws = new WebSocket(API_BASE.replace(/^http/, 'ws') + '/api/notifications/ws');

        ws.onmessage = (event) => {
            try {
                const newNotif = JSON.parse(event.data);
                setNotifications(prev => [newNotif, ...prev]);

                // Optionally play a soft sound or show browser notification
                if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
                    new Notification('Hash Out', { body: `${newNotif.actor} ${newNotif.message}` });
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
