import { useState } from "react";
import type { ChatSource } from "../../types/chat";

export function SourcesList({
  sources,
}: {
  sources: ChatSource[];
}) {
  const [open, setOpen] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-5 border-t border-slate-200 pt-4">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="
          flex items-center gap-2
          text-sm font-semibold
          text-[#163A6B]
          transition
          hover:text-[#7A1533]
        "
      >
        <span
          className={`transition-transform duration-300 ${
            open ? "rotate-90" : ""
          }`}
        >
          ▶
        </span>

        {open
          ? "Hide Sources"
          : `Sources (${sources.length})`}
      </button>

      {open && (
        <div className="mt-4 space-y-3 animate-fade-in-up">
          {sources.map((source, index) => (
            <div
              key={`${source.document}-${source.page_number}-${index}`}
              className="
                rounded-2xl
                border
                border-slate-200
                bg-slate-50
                p-4
                shadow-sm
                transition-all
                hover:border-[#163A6B]
                hover:shadow-md
              "
            >
              <div className="flex items-start justify-between gap-3">

                <div className="flex-1">

                  <h4 className="font-semibold text-[#163A6B]">
                    {source.heading || "Untitled Section"}
                  </h4>

                  <p className="mt-2 text-sm text-slate-600">
                    {source.document}
                  </p>

                </div>

                <div className="rounded-full bg-[#163A6B] px-3 py-1 text-xs font-semibold text-white">
                  Page {source.page_number}
                </div>
              </div>

              {source.score != null && (
                <div className="mt-3 text-xs text-slate-500">
                  Relevance Score:{" "}
                  <span className="font-semibold">
                    {source.score.toFixed(2)}
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}