import { useAuth } from "../context/AuthContext";
import { ActiveProspectusCard } from "../components/admin/ActiveProspectusCard";
import { UploadArea } from "../components/admin/UploadArea";

export function AdminDashboardPage() {
  const { session } = useAuth();
  const activeDocument = null;
  const documentsConnected = false;
  const loading = false;

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
        </div>
      )}
    </div>
  );
}
