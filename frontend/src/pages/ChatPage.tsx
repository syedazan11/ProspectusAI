import {
  useEffect,
  useState,
} from "react";
import { ChatWindow } from "../components/chat/ChatWindow";
import { ChatSidebar } from "../components/chat/ChatSidebar";
import {
  deleteChat,
  listChats,
  renameChat,
} from "../services/chatService";
import type { ChatSummary } from "../types/chat";

export function ChatPage() {
  const [activeChatId, setActiveChatId] =
    useState<string | null>(null);
  const [chats, setChats] = useState<
    ChatSummary[]
  >([]);
  const [isLoadingChats, setIsLoadingChats] =
    useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadChats() {
      try {
        const loadedChats = await listChats();

        if (cancelled) {
          return;
        }

        setChats(loadedChats);

        if (loadedChats.length > 0) {
          setActiveChatId(
            (current) =>
              current ?? loadedChats[0].id,
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoadingChats(false);
        }
      }
    }

    void loadChats();

    return () => {
      cancelled = true;
    };
  }, []);

  function handleNewChat() {
    setActiveChatId(null);
  }

  async function handleRename(
    chatId: string,
    title: string,
  ) {
    await renameChat(chatId, title);

    const loadedChats = await listChats();
    setChats(loadedChats);
  }

  async function handleDelete(
    chatId: string,
  ) {
    await deleteChat(chatId);

    const loadedChats = await listChats();
    setChats(loadedChats);

    if (activeChatId === chatId) {
      setActiveChatId(
        loadedChats[0]?.id ?? null,
      );
    }
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-64px)] max-w-6xl gap-4 px-4 py-4 sm:px-6">
      <div className="hidden h-full md:block">
        <ChatSidebar
          chats={chats}
          activeChatId={activeChatId}
          isLoading={isLoadingChats}
          onSelect={setActiveChatId}
          onNewChat={handleNewChat}
          onRename={handleRename}
          onDelete={handleDelete}
        />
      </div>

      <main className="min-w-0 flex-1">
        <div className="mx-auto h-full max-w-2xl">
          <ChatWindow
            activeChatId={activeChatId}
            onActiveChatChange={
              setActiveChatId
            }
            onChatsChange={setChats}
          />
        </div>
      </main>
    </div>
  );
}
