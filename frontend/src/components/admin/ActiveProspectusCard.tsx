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
  const status = document?.status?.toLowerCase();

  const statusStyle =
    status === "ready"
      ? "bg-green-100 text-green-700"
      : status === "processing"
      ? "bg-blue-100 text-blue-700"
      : status === "failed"
      ? "bg-red-100 text-red-700"
      : "bg-slate-100 text-slate-600";

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-md">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-[#163A6B]">
            Active Prospectus
          </h3>

          <p className="mt-1 text-sm text-slate-500">
            Currently available for student queries
          </p>
        </div>

        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${statusStyle}`}
        >
          {loading
            ? "Loading"
            : document?.status ?? "None"}
        </span>
      </div>

      {loading ? (
        <div className="space-y-3 animate-pulse">
          <div className="h-5 w-2/3 rounded bg-slate-200" />
          <div className="h-4 w-1/2 rounded bg-slate-200" />
          <div className="h-4 w-3/4 rounded bg-slate-200" />
        </div>
      ) : document ? (
        <div className="space-y-4">
          <div className="rounded-2xl bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Document ID
            </p>

            <p className="mt-1 text-base font-semibold text-slate-800">
              {document.document_id}
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Academic Year
              </p>

              <p className="mt-1 text-lg font-bold text-[#163A6B]">
                {document.year}
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                File Name
              </p>

              <p className="mt-1 break-all text-sm text-slate-700">
                {document.filename}
              </p>
            </div>
          </div>

          {document.official_url && (
            <a
              href={document.official_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-xl bg-[#163A6B] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#0f2d55]"
            >
              📄 Open Official Prospectus
            </a>
          )}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
          <div className="mb-3 text-4xl">📚</div>

          <h4 className="text-lg font-semibold text-slate-700">
            No Active Prospectus
          </h4>

          <p className="mt-2 text-sm text-slate-500">
            Upload and process a prospectus to make it available for the chatbot.
          </p>
        </div>
      )}
    </div>
  );
}