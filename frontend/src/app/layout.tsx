import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import { AuthProvider } from "@/lib/auth";
import { WebSocketProvider } from "@/lib/WebSocketProvider";
import Script from "next/script";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Boards — Modern Discussion Forum",
  description: "A premium discussion forum for thoughtful conversations. Create boards, start topics, and engage with a vibrant community.",
  keywords: "forum, discussion, boards, community, topics",
  manifest: "/manifest.json",
};

export const viewport = {
  themeColor: "#0ea5e9",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const adsenseClientId = process.env.NEXT_PUBLIC_ADSENSE_CLIENT_ID || "";

  return (
    <html lang="en" className={inter.variable}>
      <head>
        {adsenseClientId && (
          <Script
            async
            src={`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${adsenseClientId}`}
            crossOrigin="anonymous"
            strategy="afterInteractive"
          />
        )}
      </head>
      <body>
        <AuthProvider>
          <WebSocketProvider>
            <Navbar />
            <main>{children}</main>
            <footer className="footer">
              <div className="container">
                <p className="footer-text">
                  &copy; {new Date().getFullYear()} Boards. Built with Next.js, FastAPI &amp; Django.
                </p>
              </div>
            </footer>
          </WebSocketProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
