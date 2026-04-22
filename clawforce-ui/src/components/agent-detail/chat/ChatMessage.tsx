import { MarkdownPreview } from "../workspace/MarkdownPreview";
import type { ChatMessage as ChatMessageT } from "./types";

function PendingDots() {
  return (
    <span className="inline-flex items-center gap-1 py-1" aria-label="Assistant is thinking">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-claude-text-muted [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-claude-text-muted [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-claude-text-muted" />
    </span>
  );
}

export function ChatMessage({ message }: { message: ChatMessageT }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md bg-claude-accent px-4 py-2 text-sm text-white whitespace-pre-wrap break-words">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] rounded-2xl rounded-bl-md bg-claude-surface ring-1 ring-claude-border px-1 py-1 text-sm text-claude-text-primary">
        {message.pending ? (
          <div className="px-3 py-2">
            <PendingDots />
          </div>
        ) : message.error ? (
          <div className="px-3 py-2 text-xs text-red-600">
            <span className="font-medium">Failed:</span> {message.error}
          </div>
        ) : (
          <div className="[&>div]:p-3 [&>div]:h-auto">
            <MarkdownPreview content={message.content} />
          </div>
        )}
      </div>
    </div>
  );
}
