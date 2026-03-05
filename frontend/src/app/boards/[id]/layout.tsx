import { Metadata } from 'next';

interface LayoutProps {
    children: React.ReactNode;
    params: Promise<{ id: string }>;
}

export async function generateMetadata(props: LayoutProps): Promise<Metadata> {
    try {
        const resolvedParams = await props.params;
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/boards/${resolvedParams.id}`);
        if (!res.ok) return { title: 'Board Not Found - Boards Forum' };
        const board = await res.json();
        return {
            title: `${board.name} - Boards Forum`,
            description: board.description,
        };
    } catch (err) {
        return { title: 'Boards Forum' };
    }
}

export default function BoardLayout({ children }: LayoutProps) {
    return <>{children}</>;
}
