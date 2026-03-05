import { Metadata } from 'next';

interface LayoutProps {
    children: React.ReactNode;
    params: Promise<{ id: string }>;
}

export async function generateMetadata(props: LayoutProps): Promise<Metadata> {
    try {
        const resolvedParams = await props.params;
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/topics/${resolvedParams.id}`);
        if (!res.ok) return { title: 'Topic Not Found - Boards Forum' };
        const topic = await res.json();
        return {
            title: `${topic.subject} - Boards Forum`,
            description: `Discussion started by ${topic.starter.username} in ${topic.board_name}`,
        };
    } catch (err) {
        return { title: 'Boards Forum' };
    }
}

export default function TopicLayout({ children }: LayoutProps) {
    return <>{children}</>;
}
