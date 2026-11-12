import { Suspense } from "react";
import SearchPage from "@/components/SearchPage";

export default function Home() {
  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        Search Supreme Court of India judgments (2024 onwards) by describing your case. Every result shows the
        paragraph that matched.
      </p>
      <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
        <SearchPage />
      </Suspense>
    </div>
  );
}
