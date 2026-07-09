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
  const [editingId, setEditingId] =
    useState<string | null>(null);
  const [editingTitle, setEditingTitle] =
    useState("");

  function startRename(chat: ChatSummary) {
    setEditingId(chat.id);
    setEditingTitle(chat.title);
  }

  async function submitRename(
    chatId: string,
  ) {
    const title = editingTitle.trim();

    if (!title) {
      return;
    }

    await onRename(chatId, title);
    setEditingId(null);
    setEditingTitle("");
  }

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col rounded-2xl border border-white/70 bg-white/75 p-3 shadow-card backdrop-blur-md">
      <button
        type="button"
        onClick={onNewChat}
        className="mb-3 flex w-full items-center justify-center gap-2 rounded-xl bg-brand-gradient px-4 py-2.5 text-sm font-semibold text-white shadow-soft transition hover:opacity-90"
      >
        <span className="text-lg leading-none">+</span>
        New chat
      </button>

      <div className="mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
        Your chats
      </div>

      <div className="chat-scroll flex-1 space-y-1 overflow-y-auto">
        {isLoading && (
          <div className="px-2 py-3 text-sm text-slate-400">
            Loading chats...
          </div>
        )}

        {!isLoading && chats.length === 0 && (
          <div className="px-2 py-3 text-sm leading-5 text-slate-400">
            Your conversations will appear here.
          </div>
        )}

        {chats.map((chat) => {
          const isActive =
            chat.id === activeChatId;

          return (
            <div
              key={chat.id}
              className={`group rounded-xl transition ${
                isActive
                  ? "bg-brand-blue/10"
                  : "hover:bg-slate-100/80"
              }`}
            >
              {editingId === chat.id ? (
                <form
                  className="p-2"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void submitRename(chat.id);
                  }}
                >
                  <input
                    autoFocus
                    value={editingTitle}
                    onChange={(event) =>
                      setEditingTitle(
                        event.target.value,
                      )
                    }
                    onBlur={() =>
                      void submitRename(chat.id)
                    }
                    className="w-full rounded-lg border border-brand-blue/30 bg-white px-2 py-1.5 text-sm text-slate-700 outline-none focus:border-brand-blue"
                  />
                </form>
              ) : (
                <div className="flex items-center gap-1 p-1">
                  <button
                    type="button"
                    onClick={() =>
                      onSelect(chat.id)
                    }
                    className={`min-w-0 flex-1 truncate rounded-lg px-2 py-2 text-left text-sm ${
                      isActive
                        ? "font-medium text-brand-blue"
                        : "text-slate-600"
                    }`}
                    title={chat.title}
                  >
                    {chat.title}
                  </button>

                  <div className="flex shrink-0 opacity-0 transition group-hover:opacity-100">
                    <button
                      type="button"
                      onClick={() =>
                        startRename(chat)
                      }
                      className="rounded-md px-1.5 py-1 text-xs text-slate-400 hover:bg-white hover:text-brand-blue"
                      title="Rename chat"
                    >
                      ✎
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        if (
                          window.confirm(
                            "Delete this chat?",
                          )
                        ) {
                          void onDelete(chat.id);
                        }
                      }}
                      className="rounded-md px-1.5 py-1 text-xs text-slate-400 hover:bg-white hover:text-rose-500"
                      title="Delete chat"
                    >
                      ×
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
