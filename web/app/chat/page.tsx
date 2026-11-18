"use client";
import { useState } from "react";
import { fetchAuthSession, signOut } from "aws-amplify/auth";

type Message = { who: "you" | "ai"; text: string; cites?: string[]; error?: boolean };

// Same origin by default: the dev proxy (next.config.ts) locally, the shared domain in prod.
const API = process.env.NEXT_PUBLIC_API ?? "";

export default function Chat() {
  const [log, setLog] = useState<Message[]>([]);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const text = msg.trim();
    if (!text || busy) return;
    setLog((l) => [...l, { who: "you", text }]);
    setMsg("");
    setBusy(true);
    try {
      // The ID token carries custom:client_id. The service reads the client from it, never from the body.
      const { tokens } = await fetchAuthSession();
      const res = await fetch(`${API}/client_service/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${tokens?.idToken}` },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok) throw new Error(res.status === 401 ? "Your session expired. Sign in again." : `The assistant is unavailable (${res.status}).`);
      const body = await res.json();
      setLog((l) => [...l, { who: "ai", text: body.output_text || "Sorry, I couldn't answer that. Please talk to a person.", cites: body.citations }]);
    } catch (err) {
      setLog((l) => [...l, { who: "ai", text: (err as Error).message, error: true }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="chat">
      <header>
        <h1>Policy assistant</h1>
        <button onClick={() => signOut()}>Sign out</button>
      </header>
      <p className="disclosure">
        You are talking to an AI assistant. It answers from your own policy documents and can&apos;t change your
        policy or decide a claim. <a href="/talk-to-a-person">Talk to a person</a> at any time.
      </p>
      <section className="log" aria-live="polite">
        {log.map((m, i) => (
          <div key={i} className={`msg ${m.who}${m.error ? " error" : ""}`}>
            <b>{m.who === "you" ? "You" : "Assistant (AI)"}:</b> {m.text}
            {m.cites?.length ? (
              <div className="cites">
                {m.cites.map((c) => <code key={c} title={c}>{c.split("#")[1] ?? c}</code>)}
              </div>
            ) : null}
          </div>
        ))}
        {busy && <div className="msg ai">Looking at your policy…</div>}
      </section>
      <form onSubmit={send}>
        <input value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Ask about your policy" maxLength={2000} aria-label="Message" />
        <button type="submit" disabled={busy || !msg.trim()}>Send</button>
      </form>
    </main>
  );
}
