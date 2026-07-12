import type { ProcessingSummary } from "../../types/admin";

interface SummaryCardsProps {
  summary: ProcessingSummary | null;
  isConnected: boolean;
}

const CARD_CONFIG: {
  key: keyof ProcessingSummary;
  label: string;
  color: string;
  bg: string;
  icon: string;
}[] = [
  {
    key: "total_pages",
    label: "Total Pages",
    color: "text-[#163A6B]",
    bg: "bg-blue-50",
    icon: "📄",
  },
  {
    key: "processed_pages",
    label: "Processed",
    color: "text-green-600",
    bg: "bg-green-50",
    icon: "✅",
  },
  {
    key: "failed_pages",
    label: "Failed",
    color: "text-red-600",
    bg: "bg-red-50",
    icon: "❌",
  },
  {
    key: "quarantined_pages",
    label: "Quarantined",
    color: "text-amber-600",
    bg: "bg-amber-50",
    icon: "⚠️",
  },
];

export function SummaryCards({
  summary,
  isConnected,
}: SummaryCardsProps) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-md">
      <div className="mb-6">
        <h3 className="text-lg font-bold text-[#163A6B]">
          Processing Summary
        </h3>

        <p className="mt-1 text-sm text-slate-500">
          Current processing statistics for the uploaded prospectus
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {CARD_CONFIG.map(
          ({ key, label, color, bg, icon }) => (
            <div
              key={key}
              className={`rounded-2xl border border-slate-200 ${bg} p-5 text-center transition hover:shadow-md`}
            >
              <div className="mb-2 text-2xl">
                {icon}
              </div>

              <p
                className={`text-3xl font-bold ${color}`}
              >
                {summary ? summary[key] : "—"}
              </p>

              <p className="mt-2 text-sm font-medium text-slate-600">
                {label}
              </p>
            </div>
          ),
        )}
      </div>

      {!isConnected && (
        <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-start gap-3">
            <div className="text-xl">⚠️</div>

            <div>
              <p className="font-semibold text-amber-800">
                Backend Not Connected
              </p>

              <p className="mt-1 text-sm text-amber-700">
                Processing statistics are currently placeholders.
                They will become live once the processing status
                endpoint is connected.
              </p>

              <code className="mt-3 inline-block rounded-lg bg-amber-100 px-3 py-2 text-xs text-amber-900">
                GET /api/v1/admin/processing-status/{"{document_id}"}
              </code>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}