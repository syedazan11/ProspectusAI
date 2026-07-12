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

  const [file, setFile] = useState<File | null>(null);
  const [year, setYear] = useState(
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
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-md">
      <div className="mb-6">
        <h3 className="text-lg font-bold text-[#163A6B]">
          Upload Prospectus
        </h3>

        <p className="mt-1 text-sm text-slate-500">
          Upload the latest official prospectus for
          processing and indexing.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="space-y-5"
      >
        {/* Year */}

        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">
            Academic Year
          </label>

          <input
            type="number"
            min="2000"
            max="2100"
            value={year}
            onChange={(e) =>
              setYear(Number(e.target.value))
            }
            className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-[#163A6B] focus:ring-2 focus:ring-blue-100"
            required
          />
        </div>

        {/* URL */}

        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">
            Official Prospectus URL
          </label>

          <input
            type="url"
            value={officialUrl}
            onChange={(e) =>
              setOfficialUrl(e.target.value)
            }
            placeholder="https://www.neduet.edu.pk/..."
            className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-[#163A6B] focus:ring-2 focus:ring-blue-100"
            required
          />
        </div>

        {/* Upload */}

        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">
            Prospectus PDF
          </label>

          <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50 p-8 transition hover:border-[#163A6B] hover:bg-blue-50">
            <div className="text-5xl">
              📄
            </div>

            <p className="mt-3 font-semibold text-slate-700">
              Click to choose a PDF
            </p>

            <p className="mt-1 text-sm text-slate-500">
              Only PDF files are supported
            </p>

            {file && (
              <div className="mt-4 rounded-xl bg-green-100 px-4 py-2 text-sm font-medium text-green-700">
                ✓ {file.name}
              </div>
            )}

            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={(e) =>
                setFile(
                  e.target.files?.[0] ??
                    null,
                )
              }
              className="hidden"
              required
            />
          </label>
        </div>

        {/* Button */}

        <button
          type="submit"
          disabled={
            uploading ||
            !file ||
            !officialUrl.trim()
          }
          className="w-full rounded-xl bg-[#163A6B] px-5 py-3 font-semibold text-white transition hover:bg-[#0f2d55] disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {uploading
            ? "⏳ Uploading & Processing..."
            : "⬆ Upload & Process Prospectus"}
        </button>
      </form>

      {/* Status */}

      {uploading && (
        <div className="mt-5 rounded-2xl border border-blue-200 bg-blue-50 p-4">
          <p className="font-semibold text-blue-800">
            Processing in progress
          </p>

          <p className="mt-1 text-sm text-blue-700">
            Keep this page open while the
            ingestion pipeline completes.
          </p>
        </div>
      )}

      {message && (
        <div className="mt-5 rounded-2xl border border-green-200 bg-green-50 p-4">
          <p className="font-semibold text-green-700">
            {message}
          </p>
        </div>
      )}

      {error && (
        <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4">
          <p className="font-semibold text-red-700">
            {error}
          </p>
        </div>
      )}
    </div>
  );
}