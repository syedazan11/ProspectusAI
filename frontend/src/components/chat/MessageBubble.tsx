import type { ChatMessage } from "../../types/chat";
import { SourcesList } from "./SourcesList";
import { PageReviewCard } from "./PageReviewCard";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import nedPakistanLogo from "../../assets/NED-pakistan.png";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end animate-fade-in-up">
        <div
          className="
            max-w-[85%]
            rounded-3xl
            rounded-br-md
            bg-[#163A6B]
            px-5
            py-3
            text-[15px]
            leading-7
            text-white
            shadow-lg
            sm:max-w-[70%]
            break-words
          "
        >
          {message.text}
        </div>
      </div>
    );
  }

  console.log(
    "[MESSAGE MARKDOWN]",
    JSON.stringify(message.text),
  );

  return (
    <div className="flex items-start gap-3 animate-fade-in-up">
      {/* NED Avatar */}
      <div className="mt-1 flex h-12 w-12 shrink-0 items-center justify-center">
        <img
          src={nedPakistanLogo}
          alt="NED University"
          className="h-12 w-12 object-contain"
        />
      </div>

      <div
        className={`
          max-w-[90%]
          rounded-3xl
          rounded-tl-md
          border
          px-5
          py-4
          shadow-md
          sm:max-w-[80%]
          transition-all
          ${
            message.isError
              ? "border-red-200 bg-red-50"
              : "border-slate-200 bg-white"
          }
        `}
      >
        <div
          className={`text-[15px] leading-7 ${
            message.isError
              ? "text-red-700"
              : "text-slate-700"
          }`}
        >
          <ReactMarkdown
            // remarkPlugins={[remarkGfm]}
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeKatex]}
            components={{
              h1: ({ children }) => (
                <h1 className="mb-3 mt-2 text-xl font-bold text-[#163A6B]">
                  {children}
                </h1>
              ),

              h2: ({ children }) => (
                <h2 className="mb-3 mt-5 text-lg font-bold text-[#163A6B]">
                  {children}
                </h2>
              ),

              h3: ({ children }) => (
                <h3 className="mb-2 mt-4 text-base font-semibold text-[#163A6B]">
                  {children}
                </h3>
              ),

              p: ({ children }) => (
                <p className="mb-3 last:mb-0">
                  {children}
                </p>
              ),

              ul: ({ children }) => (
                <ul className="mb-3 ml-5 list-disc space-y-1">
                  {children}
                </ul>
              ),

              ol: ({ children }) => (
                <ol className="mb-3 ml-5 list-decimal space-y-1">
                  {children}
                </ol>
              ),

              li: ({ children }) => (
                <li className="pl-1">
                  {children}
                </li>
              ),

              strong: ({ children }) => (
                <strong className="font-semibold text-slate-900">
                  {children}
                </strong>
              ),

              blockquote: ({ children }) => (
                <blockquote className="my-3 border-l-4 border-[#163A6B] pl-4 text-slate-600">
                  {children}
                </blockquote>
              ),

              table: ({ children }) => (
                <div className="my-4 overflow-x-auto rounded-lg border border-slate-200">
                  <table className="w-full border-collapse text-sm">
                    {children}
                  </table>
                </div>
              ),

              th: ({ children }) => (
                <th className="border-b border-slate-200 bg-slate-50 px-3 py-2 text-left font-semibold text-slate-800">
                  {children}
                </th>
              ),

              td: ({ children }) => (
                <td className="border-b border-slate-100 px-3 py-2">
                  {children}
                </td>
              ),

              a: ({ children, href }) => (
                <a
                  href={href}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-[#163A6B] underline underline-offset-2 hover:opacity-80"
                >
                  {children}
                </a>
              ),
            }}
          >
            {/* {message.text} */}
            {message.text.replace(
              /\\\[([\s\S]*?)\\\]/g,
              (_, formula) => `$$${formula}$$`,
            )}
          </ReactMarkdown>
        </div>

        {message.pageReferences &&
          message.pageReferences.length > 0 && (
            <div className="mt-5">
              <PageReviewCard references={message.pageReferences} />
            </div>
          )}

        {message.sources &&
          message.sources.length > 0 && (
            <div className="mt-5 border-t border-slate-100 pt-4">
              <SourcesList sources={message.sources} />
            </div>
          )}
      </div>
    </div>
  );
}