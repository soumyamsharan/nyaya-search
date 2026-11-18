import { Suspense } from "react";
import SearchPage from "@/components/SearchPage";
import { ResultSkeleton } from "@/components/ui";

export default function Home() {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        Search Supreme Court of India judgments (2024 onwards) by describing your case. Every result shows the
        paragraph that matched.
      </p>
      <Suspense fallback={<ResultSkeleton />}>
        <SearchPage />
      </Suspense>
    </div>
  );
}
