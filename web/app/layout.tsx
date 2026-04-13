import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RP-Bench",
  description: "Roleplay quality benchmark for LLMs — human validation",
};

function Nav() {
  return (
    <nav className="border-b border-[var(--border)] bg-[var(--card)]">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-6">
        <Link href="/" className="text-[var(--accent)] font-bold text-lg tracking-tight">
          RP-Bench
        </Link>
        <div className="flex gap-4 text-sm">
          <Link href="/arena" className="text-[var(--muted)] hover:text-[var(--foreground)] transition">
            Arena
          </Link>
          <Link href="/rubric" className="text-[var(--muted)] hover:text-[var(--foreground)] transition">
            Rubric Score
          </Link>
          <Link href="/results" className="text-[var(--muted)] hover:text-[var(--foreground)] transition">
            Results
          </Link>
        </div>
      </div>
    </nav>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistMono.variable} h-full antialiased dark`}>
      <body className="min-h-full flex flex-col">
        <Nav />
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
