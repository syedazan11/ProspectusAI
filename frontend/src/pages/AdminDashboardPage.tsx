import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchDocuments } from "../services/adminService";
import type { ProspectusDocument } from "../types/admin";
import { ActiveProspectusCard } from "../components/admin/ActiveProspectusCard";
import { UploadArea } from "../components/admin/UploadArea";
import { ProcessingStages } from "../components/admin/ProcessingStages";
import { SummaryCards } from "../components/admin/SummaryCards";

export function AdminDashboardPage() {
  const { session } = useAuth();
  const [activeDocument, setActiveDocument] =
    useState<ProspectusDocument | null>(null);
  const [documentsConnected, setDocumentsConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const result = await fetchDocuments();
      if (cancelled) return;
      setDocumentsConnected(result.connected && result.ok);
      if (result.ok && result.data && result.data.length > 0) {
        setActiveDocument(result.data[0]);
      }
      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-bold text-slate-800">
            Admin dashboard
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Signed in as{" "}
            <span className="font-medium text-slate-700">
              {session?.username}
            </span>{" "}
            <span className="ml-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-700">
              dev mock session
            </span>
          </p>
        </div>
      </div>

      {loading ? (
        <div className="grid gap-5 sm:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-32 animate-pulse rounded-2xl bg-white/60"
            />
          ))}
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2">
          <ActiveProspectusCard
            document={activeDocument}
            isConnected={documentsConnected}
          />
          <UploadArea />
          <ProcessingStages
            currentStage={activeDocument ? activeDocument.stage : null}
          />
          <SummaryCards
            summary={activeDocument ? activeDocument.summary : null}
            isConnected={documentsConnected}
          />
        </div>
      )}
    </div>
  );
}
