import type {
  ProspectusDocument,
} from "../../services/adminService";

interface ActiveProspectusCardProps {
  document: ProspectusDocument | null;
  loading: boolean;
}

export function ActiveProspectusCard({
  document,
  loading,
}: ActiveProspectusCardProps) {
  return (
    <div className="rounded-2xl border border-white bg-white/90 p-5 shadow-card">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-display text-sm font-semibold text-slate-800">
          Active prospectus
        </h3>

        <span className="rounded-full bg-brand-teal/10 px-2.5 py-1 text-[11px] font-medium text-teal-700">
          {loading
            ? "Loading"
            : document?.status || "None"}
        </span>
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">
          Loading active prospectus...
        </p>
      ) : document ? (
        <div>
          <p className="font-medium text-slate-700">
            {document.document_id}
          </p>

          <p className="mt-1 text-sm text-slate-500">
            Prospectus year {document.year}
          </p>

          <p className="mt-1 text-xs text-slate-400">
            {document.filename}
          </p>

          {document.official_url && (
            <a
              href={document.official_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-flex text-sm font-medium text-brand-purple hover:underline"
            >
              Open official prospectus
            </a>
          )}
        </div>
      ) : (
        <p className="text-sm text-slate-500">
          No active ready prospectus is configured.
        </p>
      )}
    </div>
  );
}
