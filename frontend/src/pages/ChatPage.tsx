import { ChatWindow } from "../components/chat/ChatWindow";

export function ChatPage() {
  return (
    <div className="mx-auto flex h-[calc(100vh-64px)] max-w-2xl flex-col px-4 py-4 sm:px-6">
      <ChatWindow />
    </div>
  );
}
