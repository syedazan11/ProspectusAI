import { useRef, useState, useEffect, type FormEvent } from "react";

interface ChatInputProps {
  onSend: (question: string) => void;
  isLoading: boolean;
}

export function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!textareaRef.current) return;

    textareaRef.current.style.height = "0px";
    textareaRef.current.style.height =
      Math.min(textareaRef.current.scrollHeight, 160) + "px";
  }, [value]);

  function submit() {
    const trimmed = value.trim();

    if (!trimmed || isLoading) return;

    onSend(trimmed);
    setValue("");

    if (textareaRef.current) {
      textareaRef.current.style.height = "48px";
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    submit();
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="
        flex items-end gap-3
        rounded-3xl
        border border-slate-200
        bg-white
        px-4
        py-3
        shadow-lg
        transition-all
        duration-200
        focus-within:border-[#163A6B]
        focus-within:ring-4
        focus-within:ring-blue-100
      "
    >
      <textarea
        ref={textareaRef}
        value={value}
        disabled={isLoading}
        rows={1}
        placeholder="Ask anything about the NED Prospectus..."
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        className="
          flex-1
          resize-none
          overflow-y-auto
          bg-transparent
          text-[15px]
          leading-6
          text-slate-700
          placeholder:text-slate-400
          focus:outline-none
          disabled:opacity-60
          min-h-[28px]
          max-h-40
        "
      />

      <button
        type="submit"
        disabled={isLoading || !value.trim()}
        className="
          flex
          h-12
          w-12
          shrink-0
          items-center
          justify-center
          rounded-full
          bg-[#163A6B]
          text-white
          shadow-md
          transition-all
          duration-200
          hover:scale-105
          hover:bg-[#1B4C8C]
          active:scale-95
          disabled:cursor-not-allowed
          disabled:opacity-50
          disabled:hover:scale-100
        "
      >
        {isLoading ? (
          <div className="flex gap-1">
            <span
              className="typing-dot h-2 w-2 rounded-full bg-white"
              style={{ animationDelay: "0ms" }}
            />
            <span
              className="typing-dot h-2 w-2 rounded-full bg-white"
              style={{ animationDelay: "150ms" }}
            />
            <span
              className="typing-dot h-2 w-2 rounded-full bg-white"
              style={{ animationDelay: "300ms" }}
            />
          </div>
        ) : (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M5 12h13M12 5l7 7-7 7"
            />
          </svg>
        )}
      </button>
    </form>
  );
}