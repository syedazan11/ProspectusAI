import { useRef, useState, type DragEvent } from "react";
import { uploadProspectus } from "../../services/adminService";

type UploadState = "idle" | "uploading" | "not_connected" | "error" | "success";

export function UploadArea() {
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    if (file.type !== "application/pdf") {
      setState("error");
      setMessage("Please upload a PDF file.");
      return;
    }

    setFileName(file.name);
    setState("uploading");
    setMessage(null);

    const result = await uploadProspectus(file);

    if (result.ok) {
      setState("success");
      setMessage("Upload received.");
    } else if (!result.connected) {
      setState("not_connected");
      setMessage(
        "This backend feature is not connected yet — the upload endpoint (POST /api/v1/admin/upload) hasn't been built. Your file was not sent anywhere."
      );
    } else {
      setState("error");
      setMessage(result.error || "Upload failed. Please try again.");
    }
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div className="rounded-2xl border border-white bg-white/90 p-5 shadow-card">
      <h3 className="mb-4 font-display text-sm font-semibold text-slate-800">
        Upload prospectus
      </h3>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-10 text-center transition-colors ${
          isDragging
            ? "border-brand-blue bg-brand-blue/5"
            : "border-slate-200 hover:border-brand-blue/40 hover:bg-slate-50"
        }`}
      >
        <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-gradient text-lg text-white shadow-soft">
          ⬆
        </span>
        <p className="text-sm font-medium text-slate-700">
          Drop a PDF here, or click to browse
        </p>
        <p className="text-xs text-slate-400">PDF files only</p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
      </div>

      {fileName && (
        <div className="mt-3 flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
          <span className="truncate text-slate-600">{fileName}</span>
          {state === "uploading" && (
            <span className="text-xs font-medium text-brand-blue">
              Uploading…
            </span>
          )}
          {state === "success" && (
            <span className="text-xs font-medium text-teal-600">Sent ✓</span>
          )}
        </div>
      )}

      {message && (
        <p
          className={`mt-3 rounded-lg px-3 py-2 text-xs ${
            state === "not_connected"
              ? "bg-amber-50 text-amber-700"
              : state === "error"
                ? "bg-rose-50 text-rose-600"
                : "bg-teal-50 text-teal-700"
          }`}
        >
          {message}
        </p>
      )}
    </div>
  );
}
