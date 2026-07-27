import { useState } from "react";
import type { ChatSummary } from "../../types/chat";

interface ChatSidebarProps {
  chats: ChatSummary[];
  activeChatId: string | null;
  isLoading: boolean;
  onSelect: (chatId: string) => void;
  onNewChat: () => void;
  onRename: (
    chatId: string,
    title: string,
  ) => Promise<void>;
  onDelete: (chatId: string) => Promise<void>;
}

export function ChatSidebar({
  chats,
  activeChatId,
  isLoading,
  onSelect,
  onNewChat,
  onRename,
  onDelete,
}: ChatSidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");

  function startRename(chat: ChatSummary) {
    setEditingId(chat.id);
    setEditingTitle(chat.title);
  }

  async function submitRename(chatId: string) {
    const title = editingTitle.trim();

    if (!title) return;

    await onRename(chatId, title);

    setEditingId(null);
    setEditingTitle("");
  }

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col rounded-3xl border border-slate-200 bg-white shadow-xl">

      {/* Header */}
      <div className="border-b border-slate-200 p-5">

        <button
          type="button"
          onClick={onNewChat}
          className="flex w-full items-center justify-center gap-2 rounded-2xl bg-[#163A6B] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#1E4F92]"
        >
          <span className="text-lg font-bold">+</span>
          New Chat
        </button>

      </div>

      {/* Title */}
      <div className="px-5 pt-5 pb-2">
        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">
          Conversation History
        </h3>
      </div>

      {/* Chat List */}
      <div className="chat-scroll flex-1 space-y-2 overflow-y-auto px-3 pb-4">

        {isLoading && (
          <div className="p-4 text-sm text-slate-400">
            Loading chats...
          </div>
        )}

        {!isLoading && chats.length === 0 && (
          <div className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
            Start your first conversation.
          </div>
        )}

        {chats.map((chat) => {
          const isActive = chat.id === activeChatId;

          return (
            <div
              key={chat.id}
              className={`group rounded-2xl transition-all ${
                isActive
                  ? "border border-[#163A6B] bg-blue-50 shadow-sm"
                  : "hover:bg-slate-50"
              }`}
            >
              {editingId === chat.id ? (
                <form
                  className="p-3"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void submitRename(chat.id);
                  }}
                >
                  <input
                    autoFocus
                    value={editingTitle}
                    onChange={(e) =>
                      setEditingTitle(e.target.value)
                    }
                    onBlur={() =>
                      void submitRename(chat.id)
                    }
                    className="w-full rounded-xl border border-[#163A6B] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-100"
                  />
                </form>
              ) : (
                <div className="flex items-center gap-2 p-2">

                  <button
                    type="button"
                    onClick={() => onSelect(chat.id)}
                    title={chat.title}
                    className={`flex-1 truncate rounded-xl px-3 py-3 text-left text-sm transition ${
                      isActive
                        ? "font-semibold text-[#163A6B]"
                        : "text-slate-700"
                    }`}
                  >
                    💬 {chat.title}
                  </button>

                  <div className="flex opacity-0 transition group-hover:opacity-100">

                    <button
                      type="button"
                      title="Rename"
                      onClick={() => startRename(chat)}
                      className="rounded-lg p-2 text-slate-500 hover:bg-white hover:text-[#163A6B]"
                    >
                      ✏️
                    </button>

                    <button
                      type="button"
                      title="Delete"
                      onClick={() => {
                        if (
                          window.confirm(
                            "Delete this conversation?"
                          )
                        ) {
                          void onDelete(chat.id);
                        }
                      }}
                      className="rounded-lg p-2 text-slate-500 hover:bg-white hover:text-red-600"
                    >
                      🗑️
                    </button>

                  </div>

                </div>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}