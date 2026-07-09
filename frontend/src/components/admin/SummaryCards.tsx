import type { ProcessingSummary } from "../../types/admin";

interface SummaryCardsProps {
  summary: ProcessingSummary | null;
  isConnected: boolean;
}

const CARD_CONFIG: {
  key: keyof ProcessingSummary;
  label: string;
  accent: string;
}[] = [
  { key: "total_pages", label: "Total pages", accent: "text-brand-blue" },
  { key: "processed_pages", label: "Processed", accent: "text-teal-600" },
  { key: "failed_pages", label: "Failed", accent: "text-rose-500" },
  {
    key: "quarantined_pages",
    label: "Quarantined",
    accent: "text-amber-500",
  },
];

export function SummaryCards({ summary, isConnected }: SummaryCardsProps) {
  return (
    <div className="rounded-2xl border border-white bg-white/90 p-5 shadow-card">
      <h3 className="mb-4 font-display text-sm font-semibold text-slate-800">
        Processing summary
      </h3>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {CARD_CONFIG.map(({ key, label, accent }) => (
          <div
            key={key}
            className="rounded-xl bg-slate-50 px-3 py-3 text-center"
          >
            <p className={`font-display text-2xl font-bold ${accent}`}>
              {summary ? summary[key] : "—"}
            </p>
            <p className="mt-0.5 text-xs text-slate-500">{label}</p>
          </div>
        ))}
      </div>

      {!isConnected && (
        <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
          This backend feature is not connected yet. Placeholder values are
          shown until{" "}
          <code className="rounded bg-amber-100 px-1 py-0.5">
            GET /api/v1/admin/processing-status/&#123;document_id&#125;
          </code>{" "}
          is available.
        </p>
      )}
    </div>
  );
}
