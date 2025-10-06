"use client";

import { useEffect, useState } from "react";

type Message = { role: "system" | "user" | "assistant"; content: string };

export default function ChatPanel({
  initialMessages,
  sessionId,
  onSend,
  sending,
}: {
  initialMessages: Message[];
  sessionId: string;
  onSend: (msg: string) => Promise<void>;
  sending: boolean;
}) {
  const [messages, setMessages] = useState<Message[]>(initialMessages || []);
  const [text, setText] = useState("");

  // 🔧 Sync with parent whenever new messages or new sessionId come in
  useEffect(() => {
    setMessages(initialMessages || []);
  }, [initialMessages, sessionId]);

  async function handleSend() {
    if (!text.trim()) return;
    const msg = text.trim();
    setText("");
    // optimistic append
    setMessages((m) => [...m, { role: "user", content: msg }]);
    await onSend(msg);
  }

  return (
    <div className="border rounded-xl bg-white p-3 max-w-3xl">
      <div className="h-80 overflow-auto space-y-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === "assistant"
                ? "bg-gray-50 p-2 rounded"
                : m.role === "user"
                ? "bg-blue-50 p-2 rounded"
                : "text-xs text-gray-500"
            }
          >
            <div className="text-xs text-gray-500 mb-1">{m.role}</div>
            <div className="whitespace-pre-wrap text-sm">{m.content}</div>
          </div>
        ))}
      </div>

      <div className="mt-3 flex gap-2">
        <input
          className="border rounded px-3 py-2 flex-1"
          placeholder="Type which vulnerability to fix and your stack details..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleSend();
            }
          }}
        />
        <button
          onClick={handleSend}
          disabled={sending}
          className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
        >
          {sending ? "Sending…" : "Send"}
        </button>
      </div>
    </div>
  );
}
