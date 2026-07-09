import {
  useState,
  type FormEvent,
} from "react";
import { useAuth } from "../../context/AuthContext";
import {
  uploadProspectus,
} from "../../services/adminService";

export function UploadArea() {
  const { session } = useAuth();

  const [file, setFile] =
    useState<File | null>(null);
  const [year, setYear] =
    useState(
      new Date().getFullYear(),
    );
  const [officialUrl, setOfficialUrl] =
    useState("");
  const [uploading, setUploading] =
    useState(false);
  const [message, setMessage] =
    useState<string | null>(null);
  const [error, setError] =
    useState<string | null>(null);

  async function handleSubmit(
    event: FormEvent,
  ) {
    event.preventDefault();

    if (!file || !session) return;

    setUploading(true);
    setMessage(null);
    setError(null);

    try {
      const result =
        await uploadProspectus(
          file,
          year,
          officialUrl.trim(),
          session,
        );

      setMessage(result.message);
      setFile(null);
      setOfficialUrl("");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Upload failed.",
      );
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-white bg-white/90 p-5 shadow-card">
      <h3 className="mb-4 font-display text-sm font-semibold text-slate-800">
        Upload prospectus
      </h3>

      <form
        onSubmit={handleSubmit}
        className="space-y-4"
      >
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">
            Prospectus year
          </label>
          <input
            type="number"
            min="2000"
            max="2100"
            value={year}
            onChange={(event) =>
              setYear(
                Number(event.target.value),
              )
            }
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
            required
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">
            Official prospectus URL
          </label>
          <input
            type="url"
            value={officialUrl}
            onChange={(event) =>
              setOfficialUrl(
                event.target.value,
              )
            }
            placeholder="https://..."
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
            required
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">
            PDF file
          </label>
          <input
            type="file"
            accept="application/pdf,.pdf"
            onChange={(event) =>
              setFile(
                event.target.files?.[0]
                  || null,
              )
            }
            className="block w-full text-sm text-slate-600"
            required
          />
        </div>

        <button
          type="submit"
          disabled={
            uploading ||
            !file ||
            !officialUrl.trim()
          }
          className="w-full rounded-xl bg-brand-gradient px-4 py-2.5 text-sm font-semibold text-white shadow-soft disabled:opacity-50"
        >
          {uploading
            ? "Uploading and processing..."
            : "Upload and process"}
        </button>
      </form>

      {uploading && (
        <p className="mt-3 rounded-lg bg-blue-50 px-3 py-2 text-xs text-blue-700">
          Ingestion is running. Keep this page open until processing finishes.
        </p>
      )}

      {message && (
        <p className="mt-3 rounded-lg bg-teal-50 px-3 py-2 text-xs text-teal-700">
          {message}
        </p>
      )}

      {error && (
        <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-600">
          {error}
        </p>
      )}
    </div>
  );
}
