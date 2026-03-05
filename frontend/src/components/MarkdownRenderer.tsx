/**
 * Markdown Renderer with GFM and smart embeds (YouTube).
 */
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
    content: string;
}

function getYouTubeId(url: string) {
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
    const match = url.match(regExp);
    return (match && match[2].length === 11) ? match[2] : null;
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
    return (
        <div className="markdown-body">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    a: ({ node, ...props }) => {
                        const href = props.href || '';
                        const ytId = getYouTubeId(href);

                        // If it's a YouTube link and the link text equals the URL (meaning it was auto-linked or pasted raw)
                        if (ytId && props.children?.toString() === href) {
                            return (
                                <div className="video-embed" style={{ position: 'relative', paddingBottom: '56.25%', height: 0, overflow: 'hidden', margin: '16px 0', borderRadius: '8px', background: '#000' }}>
                                    <iframe
                                        src={`https://www.youtube.com/embed/${ytId}`}
                                        style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none' }}
                                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                        allowFullScreen
                                    />
                                </div>
                            );
                        }

                        // Default fallback for normal links
                        return <a {...props} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent)', textDecoration: 'none' }} />;
                    },
                    img: ({ node, ...props }: any) => (
                        <img {...props} style={{ maxWidth: '100%', borderRadius: 'var(--radius-md)', margin: '16px 0' }} loading="lazy" />
                    )
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
