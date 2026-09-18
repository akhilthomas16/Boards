import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import { AuthProvider } from "@/lib/auth";
import { WebSocketProvider } from "@/lib/WebSocketProvider";
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Hash Out — Modern Discussion Forum",
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
  return (
    <html lang="en" className={inter.variable}>
      <head />
      <body>
        <AuthProvider>
          <WebSocketProvider>
            <Navbar />
            <main>{children}</main>
            <footer className="footer">
              <div className="container">
                <p className="footer-text">
                  &copy; {new Date().getFullYear()} Hash Out. Built with Next.js, FastAPI &amp; Django.
                </p>
              </div>
            </footer>
          </WebSocketProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
