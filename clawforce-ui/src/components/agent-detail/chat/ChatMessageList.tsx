import { useEffect, useRef } from "react";
import { ChatMessage } from "./ChatMessage";
import type { ChatMessage as ChatMessageT } from "./types";

export function ChatMessageList({ messages }: { messages: ChatMessageT[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, messages[messages.length - 1]?.pending, messages[messages.length - 1]?.content]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 min-h-0 flex items-center justify-center">
        <div className="text-center">
          <p className="text-sm font-medium text-claude-text-primary">Start a conversation</p>
          <p className="mt-1 text-xs text-claude-text-muted max-w-sm">
            Send a message to chat directly with this agent. Responses appear inline.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4 space-y-3">
      {messages.map((m) => (
        <ChatMessage key={m.id} message={m} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
