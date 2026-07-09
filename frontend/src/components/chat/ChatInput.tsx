import { useState, type FormEvent } from "react";

interface ChatInputProps {
  onSend: (question: string) => void;
  isLoading: boolean;
}

export function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [value, setValue] = useState("");

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setValue("");
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    submit();
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-card"
    >
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder="Ask about seats, fees, eligibility, hostels…"
        rows={1}
        disabled={isLoading}
        className="max-h-32 flex-1 resize-none bg-transparent px-2 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none disabled:opacity-60"
      />
      <button
        type="submit"
        disabled={isLoading || !value.trim()}
        className="flex shrink-0 items-center gap-1.5 rounded-xl bg-brand-gradient px-4 py-2.5 text-sm font-semibold text-white shadow-soft transition-opacity disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isLoading ? (
          <>
            <span
              className="typing-dot h-1.5 w-1.5 rounded-full bg-white"
              style={{ animationDelay: "0ms" }}
            />
            <span
              className="typing-dot h-1.5 w-1.5 rounded-full bg-white"
              style={{ animationDelay: "150ms" }}
            />
            <span
              className="typing-dot h-1.5 w-1.5 rounded-full bg-white"
              style={{ animationDelay: "300ms" }}
            />
          </>
        ) : (
          <>
            Send
            <span aria-hidden>→</span>
          </>
        )}
      </button>
    </form>
  );
}
