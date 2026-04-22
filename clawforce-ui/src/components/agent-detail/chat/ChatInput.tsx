import { useRef, useState, type KeyboardEvent } from "react";

export function ChatInput({
  disabled,
  onSend,
  placeholder,
}: {
  disabled: boolean;
  onSend: (text: string) => void;
  placeholder?: string;
}) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="shrink-0 border-t border-claude-border bg-white p-3">
      <div className="flex items-end gap-2 rounded-xl border border-claude-border bg-white px-3 py-2 focus-within:ring-2 focus-within:ring-claude-accent/30 focus-within:border-claude-accent">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            const el = e.target;
            el.style.height = "auto";
            el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
          }}
          onKeyDown={onKeyDown}
          placeholder={placeholder ?? "Type a message…"}
          rows={1}
          disabled={disabled}
          className="flex-1 resize-none bg-transparent text-sm text-claude-text-primary placeholder:text-claude-text-muted focus:outline-none disabled:opacity-60"
        />
        <button
          type="button"
          onClick={submit}
          disabled={disabled || value.trim().length === 0}
          className="shrink-0 rounded-lg bg-claude-accent px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-claude-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          Send
        </button>
      </div>
      <p className="mt-1.5 text-[11px] text-claude-text-muted">
        Enter to send · Shift+Enter for newline
      </p>
    </div>
  );
}
