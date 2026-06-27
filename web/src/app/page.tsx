"use client";

import { FormEvent, useMemo, useRef, useState } from "react";
import {
  createSession,
  endSession,
  playVoiceTurn,
  type Difficulty,
  type Persona,
  type SessionDebrief,
  type SessionState,
} from "@/lib/voiceTrainer";

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  onresult: ((event: { results: { 0: { transcript: string } }[] }) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

const personas: { id: Persona; label: string; detail: string }[] = [
  { id: "difficult_client", label: "Difficult client", detail: "resists hard advice" },
  { id: "impatient_partner", label: "Impatient partner", detail: "demands the short answer" },
  { id: "regulator", label: "Regulator", detail: "tests safeguards and risk" },
];

const difficulties: { id: Difficulty; label: string }[] = [
  { id: "warmup", label: "Warmup" },
  { id: "live", label: "Live" },
  { id: "crossfire", label: "Crossfire" },
];

export default function Home() {
  const [persona, setPersona] = useState<Persona>("difficult_client");
  const [difficulty, setDifficulty] = useState<Difficulty>("live");
  const [session, setSession] = useState<SessionState>(() => createSession());
  const [draft, setDraft] = useState("");
  const [listening, setListening] = useState(false);
  const [voiceError, setVoiceError] = useState("");
  const [debrief, setDebrief] = useState<SessionDebrief | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  const voiceAvailable = useMemo(() => {
    if (typeof window === "undefined") return false;
    return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
  }, []);

  const lastReply = session.messages.filter((message) => message.role === "sparring").at(-1)?.text ?? "";

  function startSession() {
    const next = createSession(persona, difficulty);
    setSession(next);
    setDraft("");
    setVoiceError("");
    setDebrief(null);
    speak(next.messages[0].text);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    send(draft);
  }

  function send(text: string) {
    const cleaned = text.trim();
    if (!cleaned) return;
    let reply = "";
    setSession((current) => {
      const next = playVoiceTurn(current, cleaned);
      reply = next.messages.at(-1)?.text ?? "";
      return next;
    });
    setDraft("");
    setDebrief(null);
    window.setTimeout(() => speak(reply), 0);
  }

  function toggleListening() {
    if (!voiceAvailable) return;
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const Recognition = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!Recognition) return;
    const recognition = new Recognition();
    recognition.lang = "en-GB";
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript ?? "";
      setDraft(transcript);
      send(transcript);
    };
    recognition.onerror = () => {
      setVoiceError("Microphone capture failed. Use text input for this drill.");
      setListening(false);
    };
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    setVoiceError("");
    try {
      recognition.start();
      setListening(true);
    } catch {
      setVoiceError("Microphone could not start. Use text input for this drill.");
      setListening(false);
    }
  }

  function speak(text: string) {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.02;
    utterance.pitch = 0.92;
    window.speechSynthesis.speak(utterance);
  }

  return (
    <main className="min-h-screen bg-[#f7f8fb] text-[#151922]">
      <section className="mx-auto grid min-h-screen w-full max-w-7xl gap-5 px-4 py-5 md:px-6 lg:grid-cols-[330px_minmax(0,1fr)] lg:px-8">
        <aside className="space-y-4">
          <header className="rounded-md bg-[#151922] p-5 text-white">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#9dd6ff]">Crucible</p>
            <h1 className="mt-3 text-3xl font-semibold">Voice sparring</h1>
            <p className="mt-3 text-sm leading-6 text-[#c9d4e5]">
              Practise concise legal advice out loud, with text controls always available.
            </p>
          </header>

          <Panel title="Persona">
            <div className="grid gap-2">
              {personas.map((item) => (
                <button
                  className={item.id === persona ? "choice active" : "choice"}
                  key={item.id}
                  onClick={() => setPersona(item.id)}
                  type="button"
                >
                  <span>{item.label}</span>
                  <small>{item.detail}</small>
                </button>
              ))}
            </div>
          </Panel>

          <Panel title="Difficulty">
            <div className="grid grid-cols-3 gap-2">
              {difficulties.map((item) => (
                <button
                  className={item.id === difficulty ? "seg active" : "seg"}
                  key={item.id}
                  onClick={() => setDifficulty(item.id)}
                  type="button"
                >
                  {item.label}
                </button>
              ))}
            </div>
            <button className="primary-button mt-4 w-full" onClick={startSession} type="button">
              Start voice drill
            </button>
          </Panel>

          <Panel title="Voice state">
            <p className="text-sm leading-6 text-[#5f6978]">
              Speech recognition: {voiceAvailable ? "available in this browser" : "not available here"}.
              Spoken replies use browser speech synthesis when allowed.
            </p>
            {voiceError ? <p className="mt-3 text-sm font-semibold text-[#912323]">{voiceError}</p> : null}
          </Panel>
        </aside>

        <section className="grid gap-5 lg:grid-rows-[auto_1fr]">
          <div className="rounded-md border border-[#dce3ee] bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-2xl font-semibold">Live voice loop</h2>
                <p className="mt-1 text-sm text-[#687387]">
                  Score {session.score}/100 · turn {session.turn} · browser-native voice layer
                </p>
              </div>
              <button
                className={listening ? "danger-button" : "primary-button"}
                disabled={!voiceAvailable}
                onClick={toggleListening}
                type="button"
              >
                {listening ? "Stop listening" : "Use microphone"}
              </button>
            </div>
            <blockquote className="mt-5 rounded-md bg-[#edf6ff] p-4 text-lg leading-8 text-[#172033]">
              {lastReply}
            </blockquote>
          </div>

          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
            <section className="flex min-h-[520px] flex-col rounded-md border border-[#dce3ee] bg-white shadow-sm">
              <div className="flex-1 space-y-4 overflow-y-auto p-5">
                {session.messages.map((message, index) => (
                  <article className={message.role === "user" ? "message user" : "message sparring"} key={index}>
                    <span>{message.role === "user" ? "You" : "Sparring partner"}</span>
                    <p>{message.text}</p>
                  </article>
                ))}
              </div>
              <form className="border-t border-[#e5ebf3] p-4" onSubmit={submit}>
                <textarea
                  className="field min-h-24"
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder="Try: I understand the commercial pressure, but I recommend we do not sign until the breach risk is documented and the vendor accepts a remediation condition."
                />
                <div className="mt-3 flex flex-wrap justify-end gap-2">
                  <button className="secondary-button" onClick={() => speak(lastReply)} type="button">
                    Replay partner
                  </button>
                  <button className="secondary-button" onClick={() => setDebrief(endSession(session))} type="button">
                    End drill
                  </button>
                  <button className="primary-button" type="submit">Send text</button>
                </div>
              </form>
            </section>

            <aside className="space-y-4">
              <Panel title="Live feedback">
                <div className="space-y-3">
                  {session.events.map((event) => (
                    <article className="event" key={event.turn}>
                      <div className="flex items-center justify-between">
                        <strong>Turn {event.turn}</strong>
                        <span className={event.points >= 0 ? "points up" : "points down"}>
                          {event.points >= 0 ? `+${event.points}` : event.points}
                        </span>
                      </div>
                      <p>{event.note}</p>
                    </article>
                  ))}
                </div>
              </Panel>

              <Panel title="Debrief">
                {debrief ? (
                  <div className="space-y-3 text-sm leading-6 text-[#4d5869]">
                    <p className="font-mono text-3xl font-semibold text-[#151922]">{debrief.score}/100</p>
                    <p>{debrief.summary}</p>
                    <p><strong>Best moment:</strong> {debrief.bestMoment}</p>
                    <p><strong>Next drill:</strong> {debrief.nextDrill}</p>
                  </div>
                ) : (
                  <p className="text-sm leading-6 text-[#687387]">End the drill to see coaching notes.</p>
                )}
              </Panel>
            </aside>
          </div>
        </section>
      </section>
    </main>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-md border border-[#dce3ee] bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-[#315c8a]">{title}</h2>
      {children}
    </section>
  );
}
