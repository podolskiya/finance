// app/layout.tsx
import type { Metadata } from "next";
import { Inter } from 'next/font/google';
import "./globals.css";
import { Providers } from "./providers";
import { Sidebar } from "../components/sidebar";

// 1. Initialize the font
const inter = Inter({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700', '800'],
  variable: '--font-sans', // This directly maps to your Tailwind CSS theme variable!
});

export const metadata: Metadata = {
  title: "TradeSmart Pro",
  description: "Advanced algorithmic trading & equity analysis platform",
};

export default function RootLayout({
  children,
}: { children: React.ReactNode }) {
  return (
    // 2. Inject the font's CSS variable class here into the <html> tag
    <html lang="en" className={inter.variable}>
      <body>
        <Providers>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 p-8">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}