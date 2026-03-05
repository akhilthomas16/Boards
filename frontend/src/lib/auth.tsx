/**
 * JWT authentication utilities and React context.
 */
'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { apiFetch, setTokens, clearTokens, getTokens } from './api';

interface User {
    id: number;
    username: string;
    email: string;
}

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    login: (username: string, password: string) => Promise<void>;
    signup: (username: string, email: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        // Check for existing token on mount
        const { access } = getTokens();
        if (access) {
            apiFetch<User>('/api/auth/me')
                .then(setUser)
                .catch(() => clearTokens())
                .finally(() => setIsLoading(false));
        } else {
            setIsLoading(false);
        }
    }, []);

    const login = async (username: string, password: string) => {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const res = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/auth/token`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData.toString(),
            }
        );

        if (!res.ok) {
            const error = await res.json().catch(() => ({ detail: 'Login failed' }));
            throw new Error(error.detail || 'Login failed');
        }

        const data = await res.json();
        setTokens(data.access_token, data.refresh_token);

        const user = await apiFetch<User>('/api/auth/me');
        setUser(user);
    };

    const signup = async (username: string, email: string, password: string) => {
        await apiFetch('/api/auth/signup', {
            method: 'POST',
            body: JSON.stringify({ username, email, password }),
            skipAuth: true,
        });
        await login(username, password);
    };

    const logout = () => {
        clearTokens();
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
