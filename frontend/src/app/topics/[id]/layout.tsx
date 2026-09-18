import { Metadata } from 'next';
import { fetchApi } from '@/lib/server-api';
import type { Topic } from '@/types';

interface LayoutProps {
    children: React.ReactNode;
    params: Promise<{ id: string }>;
}

export async function generateMetadata(props: LayoutProps): Promise<Metadata> {
    try {
        const { id } = await props.params;
        const topic = await fetchApi<Topic>(`/api/topics/${id}`);
        return {
            title: `${topic.subject} - Hash Out`,
            description: `Discussion started by ${topic.starter.username} in ${topic.board_name}`,
        };
    } catch {
        return { title: 'Topic Not Found - Hash Out' };
    }
}

export default function TopicLayout({ children }: LayoutProps) {
    return <>{children}</>;
}
