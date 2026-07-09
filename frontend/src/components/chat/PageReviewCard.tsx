import type { PageReference } from "../../types/chat";
import { buildPageUrl } from "../../services/api";

export function PageReviewCard({
  references,
}: {
  references: PageReference[];
}) {
  if (!references || references.length === 0) {
    return null;
  }

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {references.map((ref, index) => {
        const href = ref.page_url?.startsWith("http")
          ? ref.page_url
          : ref.page_url
            ? buildPageUrl(ref.page_url)
            : "#";

        return (
          <a
            key={`${ref.document}-${ref.page_number}-${index}`}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-gradient px-3.5 py-2 text-sm font-semibold text-white shadow-sm transition hover:opacity-90"
          >
            {ref.page_number
              ? `Open page ${ref.page_number}`
              : "Open official prospectus"}
            <span aria-hidden>&rarr;</span>
          </a>
        );
      })}
    </div>
  );
}
