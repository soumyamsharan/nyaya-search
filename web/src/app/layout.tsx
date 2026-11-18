import type { Metadata } from "next";
import { IBM_Plex_Sans, Newsreader } from "next/font/google";
import Link from "next/link";
import NotesBar from "@/components/NotesBar";
import "./globals.css";

const plex = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-plex" });
const newsreader = Newsreader({ subsets: ["latin"], variable: "--font-newsreader", style: ["normal", "italic"] });

export const metadata: Metadata = {
  title: "Nyaya Search",
  description: "Find Supreme Court of India precedents from the facts of your case, pinned to the paragraph.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${plex.variable} ${newsreader.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <header className="border-b border-rule bg-paper/95 backdrop-blur-sm">
          <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-x-6 gap-y-3 px-5 py-4">
            <div className="flex items-baseline gap-6">
              <Link href="/" className="font-serif text-2xl font-medium tracking-tight text-ink">
                Nyaya Search
              </Link>
              <Link href="/statutes" className="text-sm text-ink-soft hover:text-accent">
                Statutes
              </Link>
            </div>
            <NotesBar />
          </div>
        </header>
        <main className="mx-auto w-full max-w-3xl flex-1 px-5 pb-16 pt-10">{children}</main>
        <footer className="border-t border-rule">
          <div className="mx-auto max-w-3xl space-y-1.5 px-5 py-6 text-xs leading-relaxed text-muted">
            <p>
              Judgments from the{" "}
              <a
                href="https://registry.opendata.aws/indian-supreme-court-judgments/"
                className="underline decoration-rule underline-offset-2 hover:text-accent"
                target="_blank"
                rel="noopener noreferrer"
              >
                Indian Supreme Court Judgments
              </a>{" "}
              open dataset, licensed CC-BY-4.0. Credit to its maintainers.
            </p>
            <p>Nyaya Search is a research aid, not legal advice. Read each judgment before citing it.</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
