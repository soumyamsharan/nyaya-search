import type { Metadata } from "next";
import Link from "next/link";
import NotesBar from "@/components/NotesBar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nyaya Search",
  description: "Find Supreme Court of India precedents from the facts of your case, pinned to the paragraph.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-slate-50 text-slate-900">
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
          <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-2 px-4 py-3">
            <div className="flex items-center gap-4">
              <Link href="/" className="text-lg font-semibold text-indigo-700">
                Nyaya Search
              </Link>
              <Link href="/statutes" className="text-sm text-slate-600 hover:text-indigo-700">
                Statutes
              </Link>
            </div>
            <NotesBar />
          </div>
        </header>
        <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-6">{children}</main>
        <footer className="border-t border-slate-200 bg-white">
          <div className="mx-auto max-w-4xl space-y-1 px-4 py-4 text-xs text-slate-500">
            <p>
              Judgments from the{" "}
              <a href="https://registry.opendata.aws/indian-supreme-court-judgments/" className="underline" target="_blank" rel="noopener noreferrer">
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
