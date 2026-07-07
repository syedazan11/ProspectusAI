import { useState } from "react";
import type { ChatSource } from "../../types/chat";

export function SourcesList({ sources }: { sources: ChatSource[] }) {
  const [open, setOpen] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 border-t border-slate-100 pt-2">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs font-medium text-brand-purple hover:text-brand-purple/80"
      >
        <span
          className={`inline-block transition-transform ${open ? "rotate-90" : ""}`}
        >
          ▸
        </span>
        {open ? "Hide sources" : `Show sources (${sources.length})`}
      </button>

      {open && (
        <ul className="mt-2 space-y-1.5">
          {sources.map((source, index) => (
            <li
              key={`${source.document}-${source.page_number}-${index}`}
              className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600"
            >
              <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                <span className="font-medium text-slate-700">
                  {source.heading || "Untitled section"}
                </span>
                <span className="rounded-full bg-brand-teal/10 px-2 py-0.5 text-[11px] font-medium text-teal-700">
                  score {source.score.toFixed(2)}
                </span>
              </div>
              <div className="mt-0.5 text-slate-500">
                {source.document} · page {source.page_number}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
