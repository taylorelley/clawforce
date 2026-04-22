import { useState } from "react";
import { api } from "../../../lib/api";
import { ChatInput } from "./ChatInput";
import { ChatMessageList } from "./ChatMessageList";
import type { ChatMessage } from "./types";

function newId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function ChatTab({ agentId }: { agentId: string; token: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);

  async function handleSend(text: string) {
    const userMsg: ChatMessage = {
      id: newId(),
      role: "user",
      content: text,
      timestamp: Date.now(),
    };
    const placeholderId = newId();
    const placeholder: ChatMessage = {
      id: placeholderId,
      role: "assistant",
      content: "",
      timestamp: Date.now(),
      pending: true,
    };
    setMessages((prev) => [...prev, userMsg, placeholder]);
    setSending(true);

    try {
      const res = await api.agents.chat(agentId, text);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === placeholderId
            ? { ...m, content: res.reply || "", pending: false, timestamp: Date.now() }
            : m,
        ),
      );
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === placeholderId
            ? { ...m, content: "", pending: false, error: detail, timestamp: Date.now() }
            : m,
        ),
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex flex-col rounded-xl border border-claude-border bg-claude-bg overflow-hidden" style={{ height: "calc(70vh + 40px)" }}>
      <ChatMessageList messages={messages} />
      <ChatInput disabled={sending} onSend={handleSend} />
    </div>
  );
}
