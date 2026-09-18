import { Metadata } from 'next';
import { fetchApi } from '@/lib/server-api';
import type { Board } from '@/types';

interface LayoutProps {
    children: React.ReactNode;
    params: Promise<{ id: string }>;
}

export async function generateMetadata(props: LayoutProps): Promise<Metadata> {
    try {
        const { id } = await props.params;
        const board = await fetchApi<Board>(`/api/boards/${id}`);
        return {
            title: `${board.name} - Hash Out`,
            description: board.description,
        };
    } catch {
        return { title: 'Board Not Found - Hash Out' };
    }
}

export default function BoardLayout({ children }: LayoutProps) {
    return <>{children}</>;
}
