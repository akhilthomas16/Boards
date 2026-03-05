/**
 * Navbar component — responsive navigation with auth state and real-time notifications.
 */
'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useAuth } from '@/lib/auth';
import { useWebSockets } from '@/lib/WebSocketProvider';

export default function Navbar() {
    const { user, logout, isLoading } = useAuth();
    const { notifications, unreadCount, markAsRead, markAllAsRead } = useWebSockets();
    const [menuOpen, setMenuOpen] = useState(false);
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const [notifOpen, setNotifOpen] = useState(false);

    return (
        <nav className="navbar">
            <div className="container navbar-inner">
                <Link href="/" className="navbar-brand">
                    <span className="brand-icon">◆</span>
                    Boards
                </Link>

                {/* Search bar */}
                <div className="navbar-search">
                    <form action="/search" method="GET">
                        <input
                            type="text"
                            name="q"
                            placeholder="Search boards, topics, posts..."
                            className="search-input"
                            autoComplete="off"
                        />
                    </form>
                </div>

                {/* Mobile toggle */}
                <button
                    className="navbar-toggle"
                    onClick={() => setMenuOpen(!menuOpen)}
                    aria-label="Toggle navigation"
                >
                    <span className="toggle-bar"></span>
                    <span className="toggle-bar"></span>
                    <span className="toggle-bar"></span>
                </button>

                {/* Nav links */}
                <div className={`navbar-links ${menuOpen ? 'active' : ''}`}>
                    {isLoading ? null : user ? (
                        <div className="user-menu" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                            <div className="notifications-dropdown" style={{ position: 'relative' }}>
                                <button
                                    className="btn btn-ghost"
                                    onClick={() => { setNotifOpen(!notifOpen); setDropdownOpen(false); }}
                                    style={{ padding: '8px', position: 'relative' }}
                                >
                                    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                                    </svg>
                                    {unreadCount > 0 && (
                                        <span style={{ position: 'absolute', top: '0', right: '0', background: 'var(--accent)', color: 'white', borderRadius: '50%', padding: '2px 6px', fontSize: '0.65rem', fontWeight: 'bold' }}>
                                            {unreadCount}
                                        </span>
                                    )}
                                </button>

                                {notifOpen && (
                                    <div className="dropdown-menu" style={{ width: '300px', right: 0, left: 'auto', maxHeight: '400px', overflowY: 'auto' }}>
                                        <div style={{ padding: '8px 16px', display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)' }}>
                                            <strong>Notifications</strong>
                                            {unreadCount > 0 && (
                                                <button className="btn btn-ghost" style={{ padding: 0, fontSize: '0.75rem' }} onClick={markAllAsRead}>Mark all read</button>
                                            )}
                                        </div>
                                        {notifications.length === 0 ? (
                                            <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                                                No notifications
                                            </div>
                                        ) : (
                                            notifications.map(notif => (
                                                <div
                                                    key={notif.id}
                                                    className="dropdown-item"
                                                    style={{ display: 'block', whiteSpace: 'normal', opacity: notif.is_read ? 0.7 : 1, background: notif.is_read ? 'transparent' : 'rgba(var(--accent-rgb), 0.1)' }}
                                                >
                                                    <Link
                                                        href={notif.link}
                                                        onClick={() => { markAsRead(notif.id); setNotifOpen(false); }}
                                                        style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}
                                                    >
                                                        <strong>{notif.actor}</strong> {notif.message}
                                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                                                            {new Date(notif.created_at).toLocaleDateString()}
                                                        </div>
                                                    </Link>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                )}
                            </div>

                            <button
                                className="user-button"
                                onClick={() => { setDropdownOpen(!dropdownOpen); setNotifOpen(false); }}
                            >
                                <span className="avatar">{user.username[0].toUpperCase()}</span>
                                {user.username}
                                <svg className="chevron" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
                                    <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" />
                                </svg>
                            </button>
                            {dropdownOpen && (
                                <div className="dropdown-menu">
                                    <Link href={`/profile/${user.username}`} className="dropdown-item" onClick={() => setDropdownOpen(false)}>
                                        My Profile
                                    </Link>
                                    <Link href="/settings" className="dropdown-item" onClick={() => setDropdownOpen(false)}>
                                        Settings
                                    </Link>
                                    <div className="dropdown-divider"></div>
                                    <button className="dropdown-item logout" onClick={() => { logout(); setDropdownOpen(false); }}>
                                        Logout
                                    </button>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="auth-buttons">
                            <Link href="/auth/login" className="btn btn-ghost">Login</Link>
                            <Link href="/auth/signup" className="btn btn-primary">Sign Up</Link>
                        </div>
                    )}
                </div>
            </div>
        </nav>
    );
}
