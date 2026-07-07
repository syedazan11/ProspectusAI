import type { ProspectusDocument } from "../../types/admin";

interface ActiveProspectusCardProps {
  document: ProspectusDocument | null;
  isConnected: boolean;
}

export function ActiveProspectusCard({
  document,
  isConnected,
}: ActiveProspectusCardProps) {
  return (
    <div className="rounded-2xl border border-white bg-white/90 p-5 shadow-card">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-display text-sm font-semibold text-slate-800">
          Active prospectus
        </h3>
        <span className="rounded-full bg-brand-teal/10 px-2.5 py-1 text-[11px] font-medium text-teal-700">
          {document ? document.stage : "None"}
        </span>
      </div>

      {document ? (
        <div>
          <p className="font-medium text-slate-700">{document.name}</p>
          <p className="mt-0.5 text-xs text-slate-500">
            Uploaded {new Date(document.uploaded_at).toLocaleDateString()}
          </p>
        </div>
      ) : (
        <p className="text-sm text-slate-500">
          No prospectus has been uploaded yet.
        </p>
      )}

      {!isConnected && (
        <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
          This backend feature is not connected yet — showing a placeholder
          state. Connect{" "}
          <code className="rounded bg-amber-100 px-1 py-0.5">
            GET /api/v1/admin/documents
          </code>{" "}
          to see real data here.
        </p>
      )}
    </div>
  );
}
