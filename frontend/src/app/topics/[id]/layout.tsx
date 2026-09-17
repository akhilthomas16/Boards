import { Metadata } from 'next';
import { API_BASE } from '@/lib/api';

interface LayoutProps {
    children: React.ReactNode;
    params: Promise<{ id: string }>;
}

export async function generateMetadata(props: LayoutProps): Promise<Metadata> {
    try {
        const resolvedParams = await props.params;
        const res = await fetch(`${API_BASE}/api/topics/${resolvedParams.id}`);
        if (!res.ok) return { title: 'Topic Not Found - Hash Out' };
        const topic = await res.json();
        return {
            title: `${topic.subject} - Hash Out`,
            description: `Discussion started by ${topic.starter.username} in ${topic.board_name}`,
        };
    } catch (err) {
        return { title: 'Hash Out' };
    }
}

export default function TopicLayout({ children }: LayoutProps) {
    return <>{children}</>;
}
