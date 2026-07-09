import {
  useEffect,
  useState,
  type FormEvent,
} from "react";
import { useAuth } from "../context/AuthContext";
import { ActiveProspectusCard } from "../components/admin/ActiveProspectusCard";
import { UploadArea } from "../components/admin/UploadArea";
import {
  createAdmin,
  deleteAdmin,
  listAdmins,
  type AdminAccount,
} from "../services/adminService";

export function AdminDashboardPage() {
  const { session } = useAuth();

  const activeDocument = null;
  const documentsConnected = false;

  const [admins, setAdmins] = useState<
    AdminAccount[]
  >([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loadingAdmins, setLoadingAdmins] =
    useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<
    string | null
  >(null);

  async function refreshAdmins() {
    if (!session) return;

    try {
      const result = await listAdmins(session);
      setAdmins(result.admins);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not load admins.",
      );
    } finally {
      setLoadingAdmins(false);
    }
  }

  useEffect(() => {
    void refreshAdmins();
  }, [session]);

  async function handleCreate(
    event: FormEvent,
  ) {
    event.preventDefault();

    if (!session) return;

    setSaving(true);
    setMessage(null);

    try {
      await createAdmin(
        username.trim(),
        password,
        session,
      );

      setUsername("");
      setPassword("");
      setMessage("Admin created successfully.");
      await refreshAdmins();
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not create admin.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(
    admin: AdminAccount,
  ) {
    if (!session) return;

    const confirmed = window.confirm(
      `Delete admin "${admin.username}"?`,
    );

    if (!confirmed) return;

    setMessage(null);

    try {
      await deleteAdmin(admin.id, session);
      setMessage("Admin deleted successfully.");
      await refreshAdmins();
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not delete admin.",
      );
    }
  }

  const maximumReached = admins.length >= 2;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <div className="mb-6">
        <h1 className="font-display text-2xl font-bold text-slate-800">
          Admin dashboard
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Signed in as{" "}
          <span className="font-medium text-slate-700">
            {session?.username}
          </span>
        </p>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <ActiveProspectusCard
          document={activeDocument}
          isConnected={documentsConnected}
        />

        <UploadArea />

        <section className="rounded-2xl bg-white p-6 shadow-soft sm:col-span-2">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="font-display text-lg font-semibold text-slate-800">
                Admin accounts
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Maximum 2 administrators.
              </p>
            </div>

            <span className="rounded-full bg-brand-purple/10 px-3 py-1 text-sm font-medium text-brand-purple">
              {admins.length} / 2
            </span>
          </div>

          {message && (
            <div className="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
              {message}
            </div>
          )}

          <div className="mt-5 space-y-3">
            {loadingAdmins ? (
              <p className="text-sm text-slate-500">
                Loading admins...
              </p>
            ) : (
              admins.map((admin) => (
                <div
                  key={admin.id}
                  className="flex items-center justify-between rounded-xl border border-slate-100 px-4 py-3"
                >
                  <div>
                    <p className="font-medium text-slate-800">
                      {admin.username}
                    </p>
                    {admin.id === session?.id && (
                      <p className="text-xs text-slate-400">
                        Current account
                      </p>
                    )}
                  </div>

                  {admin.id !== session?.id && (
                    <button
                      type="button"
                      onClick={() =>
                        void handleDelete(admin)
                      }
                      className="rounded-lg px-3 py-1.5 text-sm font-medium text-rose-500 hover:bg-rose-50"
                    >
                      Delete
                    </button>
                  )}
                </div>
              ))
            )}
          </div>

          {!maximumReached && (
            <form
              onSubmit={handleCreate}
              className="mt-6 grid gap-3 sm:grid-cols-[1fr_1fr_auto]"
            >
              <input
                value={username}
                onChange={(event) =>
                  setUsername(event.target.value)
                }
                placeholder="New admin username"
                minLength={3}
                required
                className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-brand-purple"
              />

              <input
                type="password"
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                placeholder="Password (8+ characters)"
                minLength={8}
                required
                className="rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-brand-purple"
              />

              <button
                type="submit"
                disabled={saving}
                className="rounded-xl bg-brand-gradient px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"
              >
                {saving ? "Creating..." : "Add admin"}
              </button>
            </form>
          )}

          {maximumReached && (
            <p className="mt-5 text-sm text-slate-500">
              The maximum of 2 admins has been reached.
              Delete the other admin before creating a replacement.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
