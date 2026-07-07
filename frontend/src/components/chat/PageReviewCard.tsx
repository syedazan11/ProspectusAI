import type { PageReference } from "../../types/chat";
import { buildPageUrl } from "../../services/api";

export function PageReviewCard({
  references,
}: {
  references: PageReference[];
}) {
  if (!references || references.length === 0) return null;

  return (
    <div className="mt-3 space-y-2.5">
      {references.map((ref, index) => (
        <div
          key={`${ref.document}-${ref.page_number}-${index}`}
          className="rounded-xl border border-amber-200 bg-amber-50 p-3.5 shadow-sm"
        >
          <div className="flex items-start gap-2.5">
            <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-amber-400 text-white text-xs font-bold">
              !
            </span>
            <div className="flex-1">
              <p className="text-sm font-semibold text-amber-900">
                We couldn't fully confirm this from the text — worth checking
                the page yourself
              </p>
              <p className="mt-1 text-xs text-amber-800">
                <span className="font-medium">{ref.document}</span>, page{" "}
                {ref.page_number}
              </p>
              <p className="mt-1 text-xs text-amber-700">{ref.reason}</p>
              <a
                href={buildPageUrl(ref.page_url)}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2.5 inline-flex items-center gap-1.5 rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-amber-600"
              >
                View page {ref.page_number}
                <span aria-hidden>→</span>
              </a>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
