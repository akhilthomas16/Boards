/**
 * Auth React context. The session is the API's httpOnly cookies; this only mirrors who is logged in.
 */
'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import api from './api';

import type { User } from '@/types';

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    login: (username: string, password: string) => Promise<void>;
    signup: (username: string, email: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        // The cookies are invisible to JS, so ask the API whether they hold a session.
        api.get<User>('/api/auth/me')
            .then(setUser)
            .catch(() => setUser(null))
            .finally(() => setIsLoading(false));
    }, []);

    const login = async (username: string, password: string) => {
        const user = await api.postForm<User>(
            '/api/auth/token',
            new URLSearchParams({ username, password }),
            { skipRefresh: true },
        );
        setUser(user);
    };

    const signup = async (username: string, email: string, password: string) => {
        await api.post('/api/auth/signup', { username, email, password });
        await login(username, password);
    };

    const logout = async () => {
        await api.post('/api/auth/logout', {}).catch(() => {});
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, isLoading, login, signup, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) throw new Error('useAuth must be used within AuthProvider');
    return context;
}
