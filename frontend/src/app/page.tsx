"use client";

import { useEffect, useState } from "react";
import { apiPost } from "@/lib/api";
import type { Scan } from "@/types";
import FindingCard from "@/components/FindingCard";
import Attestation from "@/components/Attestation";
// You can keep ChatPanel import for later, but we’ll show an inline chat box first.
// import ChatPanel from "@/components/ChatPanel";

const DEMO_HOSTS = new Set(["example.com", "www.example.com"]);
function hostFromUrl(u: string) {
  try { return new URL(u).host.toLowerCase(); } catch { return ""; }
}

export default function Home() {
  const [url, setUrl] = useState("https://example.com");
  const [scan, setScan] = useState<Scan | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [attest, setAttest] = useState(false);

  // chat state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[] | null>(null); // authoritative thread from server
  const [draft, setDraft] = useState(""); // inline input
  const [sending, setSending] = useState(false);

  const canScan = DEMO_HOSTS.has(hostFromUrl(url)) || attest;

  async function onScan() {
    if (!canScan) { setErr("Please attest you own or are authorized to test this domain."); return; }
    setLoading(true); setErr(null);
    setScan(null); setSessionId(null); setMessages(null); setDraft("");
    try {
      const result = await apiPost<Scan>("/scan", { url });
      setScan(result);
    } catch (e: any) {
      setErr(e?.message ?? "Scan failed");
    } finally { setLoading(false); }
  }

  async function startAssistant() {
    if (!scan) return;
    setErr(null);
    try {
      const boot = await apiPost<{ session_id: string; messages: any[]; first: string }>(
        "/llm/session",
        { scan, model: "gpt-4o-mini" }
      );
      setSessionId(boot.session_id);
      setMessages(boot.messages);
    } catch (e: any) {
      setErr(e?.message ?? "Assistant failed to start");
    }
  }

  async function sendToAssistantInline() {
    if (!sessionId || !draft.trim()) return;
    const text = draft.trim();
    setDraft("");
    // optimistic append
    setMessages((m) => (m ? [...m, { role: "user", content: text }] : [{ role: "user", content: text }]));
    setSending(true);
    try {
      const resp = await apiPost<{ reply: string; messages: any[] }>("/llm/message", {
        session_id: sessionId,
        user_message: text,
        model: "gpt-4o-mini",
      });
      setMessages(resp.messages); // replace with server’s authoritative thread
    } catch (e: any) {
      setErr(e?.message ?? "Assistant error");
    } finally {
      setSending(false);
    }
  }

  // optional: clear error when URL changes
  useEffect(() => { if (err) setErr(null); /* eslint-disable-next-line */ }, [url]);

  return (
    <main className="min-h-screen p-8 bg-gray-50">
      <h1 className="text-3xl font-bold">Hack Anything Assistant</h1>
      <p className="mt-1 text-gray-600 text-sm">
        Scan + Remediate (HSTS, CSP, CORS, Cookies, etc.). Start the AI assistant to fix issues.
      </p>

      <div className="mt-6 flex flex-col gap-3 max-w-3xl">
        <div className="flex gap-2">
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://yourdomain.com"
            className="border px-3 py-2 rounded w-[32rem] bg-white"
          />
          <button
            onClick={onScan}
            disabled={loading || !canScan}
            className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
          >
            {loading ? "Scanning…" : "Scan"}
          </button>
        </div>
        {!DEMO_HOSTS.has(hostFromUrl(url)) && (
          <Attestation checked={attest} setChecked={setAttest} />
        )}
      </div>

      {err && <div className="mt-3 text-sm text-red-700">{err}</div>}

      {scan && (
        <>
          <section className="mt-8">
            <div className="flex items-center gap-3">
              <div className="text-2xl font-semibold">Score: {scan.score}</div>
              <div className="text-gray-600 text-sm">URL: {scan.url}</div>
              <button
                onClick={startAssistant}
                className="ml-auto px-3 py-2 rounded bg-emerald-600 text-white disabled:opacity-50"
                disabled={!scan}
                title={!scan ? "Run a scan first" : "Start the remediation assistant"}
              >
                Start Assistant
              </button>
            </div>

            {/* Show thread as soon as assistant starts */}
            {sessionId && messages && (
              <div className="mt-4 border rounded p-3 bg-white">
                <h2 className="text-xl font-semibold mb-2">Remediation Assistant</h2>

                <div className="h-80 overflow-auto space-y-3 border rounded p-2 bg-gray-50">
                  {messages.map((m, i) => (
                    <div
                      key={i}
                      className={
                        m.role === "assistant"
                          ? "bg-gray-100 p-2 rounded"
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
                    placeholder="Tell me which finding to fix and your stack (e.g., Nginx + Django)…"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        sendToAssistantInline();
                      }
                    }}
                  />
                  <button
                    onClick={sendToAssistantInline}
                    disabled={sending}
                    className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
                  >
                    {sending ? "Sending…" : "Send"}
                  </button>
                </div>
              </div>
            )}

            {/* Findings list */}
            <div className="mt-4 grid gap-4">
              {scan.findings.map((f) => (
                <FindingCard key={f.id} f={f} />
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
