import { Metadata } from 'next';
import { API_BASE } from '@/lib/api';

interface LayoutProps {
    children: React.ReactNode;
    params: Promise<{ id: string }>;
}

export async function generateMetadata(props: LayoutProps): Promise<Metadata> {
    try {
        const resolvedParams = await props.params;
        const res = await fetch(`${API_BASE}/api/boards/${resolvedParams.id}`);
        if (!res.ok) return { title: 'Board Not Found - Hash Out' };
        const board = await res.json();
        return {
            title: `${board.name} - Hash Out`,
            description: board.description,
        };
    } catch (err) {
        return { title: 'Hash Out' };
    }
}

export default function BoardLayout({ children }: LayoutProps) {
    return <>{children}</>;
}
