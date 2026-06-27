"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { ChatTranscript } from "@/components/ai/ChatTranscript";
import {
  createVoiceRound,
  endVoiceRound,
  submitVoiceTurn,
  type Debrief,
  type RoundState,
  type VoiceDifficulty,
  type VoicePersona,
} from "@/lib/voiceBackend";
import { Panel } from "@/components/Panel";
import { roundTranscriptMessages } from "@/lib/aiTranscript";
import { createSpeechRecognition, hasSpeechRecognition, type SpeechRecognitionLike } from "@/lib/speech";

const personas: { id: VoicePersona; label: string; detail: string }[] = [
  { id: "difficult_client", label: "Difficult client", detail: "pressure and deadlines" },
  { id: "impatient_partner", label: "Impatient partner", detail: "flat refusal" },
  { id: "regulator", label: "Regulator", detail: "clause precision" },
];

const difficulties: { id: VoiceDifficulty; label: string }[] = [
  { id: "warmup", label: "Warmup" },
  { id: "live", label: "Live" },
  { id: "crossfire", label: "Crossfire" },
];

export default function Home() {
  const [persona, setPersona] = useState<VoicePersona>("difficult_client");
  const [difficulty, setDifficulty] = useState<VoiceDifficulty>("live");
  const [round, setRound] = useState<RoundState | null>(null);
  const [draft, setDraft] = useState("");
  const [listening, setListening] = useState(false);
  const [voiceAvailable, setVoiceAvailable] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [debrief, setDebrief] = useState<Debrief | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  useEffect(() => {
    const checkId = window.setTimeout(() => setVoiceAvailable(hasSpeechRecognition()), 0);
    return () => window.clearTimeout(checkId);
  }, []);

  const lastReply = round?.messages.filter((message) => message.role === "opponent").at(-1)?.text ?? "";
  const transcriptMessages = useMemo(() => roundTranscriptMessages(round), [round]);

  async function startSession() {
    setBusy(true);
    setError("");
    setDebrief(null);
    try {
      const next = await createVoiceRound(persona, difficulty);
      setRound(next);
      speak(next.messages.at(-1)?.text ?? "");
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void send(draft);
  }

  async function send(text: string) {
    const cleaned = text.trim();
    if (!cleaned) return;
    if (!round?.id) {
      setError("Start a credential-backed voice drill before sending a move.");
      return;
    }

    setBusy(true);
    setError("");
    try {
      const result = await submitVoiceTurn(round.id, cleaned);
      setRound(result.round);
      setDraft("");
      setDebrief(null);
      speak(result.round.messages.at(-1)?.text ?? "");
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(false);
    }
  }

  function toggleListening() {
    if (!voiceAvailable || busy) return;
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const recognition = createSpeechRecognition();
    if (!recognition) return;
    recognition.lang = "en-GB";
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript ?? "";
      setDraft(transcript);
      void send(transcript);
    };
    recognition.onerror = () => {
      setError("Microphone capture failed. The backend text path is still available.");
      setListening(false);
    };
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    setError("");
    try {
      recognition.start();
      setListening(true);
    } catch {
      setError("Microphone could not start. The backend text path is still available.");
      setListening(false);
    }
  }

  async function finish() {
    if (!round?.id) {
      setError("Start a backend round before ending the drill.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      setDebrief(await endVoiceRound(round.id));
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(false);
    }
  }

  function speak(text: string) {
    if (!text || typeof window === "undefined" || !window.speechSynthesis) return;
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
              Speak or type your move; the opponent response comes from the configured backend.
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
            <button className="primary-button mt-4 w-full" disabled={busy} onClick={() => void startSession()} type="button">
              {busy ? "Connecting..." : "Start voice drill"}
            </button>
          </Panel>

          <Panel title="Voice state">
            <p className="text-sm leading-6 text-[#5f6978]">
              Speech recognition: {voiceAvailable ? "available in this browser" : "not available here"}.
              Opponent turns require the backend API proxy and credentials.
            </p>
            {error ? <p className="mt-3 text-sm font-semibold text-[#912323]">{error}</p> : null}
          </Panel>
        </aside>

        <section className="grid gap-5 lg:grid-rows-[auto_1fr]">
          <div className="rounded-md border border-[#dce3ee] bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-2xl font-semibold">Live voice loop</h2>
                <p className="mt-1 text-sm text-[#687387]">
                  Score {round?.score ?? 0}/100 · turn {round?.turn ?? 0} · runtime {round?.runtime ?? "not connected"}
                </p>
              </div>
              <button
                className={listening ? "danger-button" : "primary-button"}
                disabled={!voiceAvailable || !round || busy}
                onClick={toggleListening}
                type="button"
              >
                {listening ? "Stop listening" : "Use microphone"}
              </button>
            </div>
            <blockquote className="mt-5 rounded-md bg-[#edf6ff] p-4 text-lg leading-8 text-[#172033]">
              {lastReply || "Start a backend voice drill to receive the first opponent move."}
            </blockquote>
          </div>

          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
            <section className="flex min-h-[520px] flex-col rounded-md border border-[#dce3ee] bg-white shadow-sm">
              <div className="flex-1 overflow-y-auto p-5">
                <ChatTranscript
                  messages={transcriptMessages}
                  emptyTitle="No backend round"
                  emptyDescription="Start a voice drill to load the credential-backed sparring partner."
                />
              </div>
              <form className="border-t border-[#e5ebf3] p-4" onSubmit={submit}>
                <textarea
                  className="field min-h-24"
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder="Speak or type the move you want the backend opponent to answer."
                  value={draft}
                />
                <div className="mt-3 flex flex-wrap justify-end gap-2">
                  <button className="secondary-button" disabled={!lastReply} onClick={() => speak(lastReply)} type="button">
                    Replay partner
                  </button>
                  <button className="secondary-button" disabled={!round || busy} onClick={() => void finish()} type="button">
                    End drill
                  </button>
                  <button className="primary-button" disabled={!round || busy} type="submit">Send text</button>
                </div>
              </form>
            </section>

            <aside className="space-y-4">
              <Panel title="Live feedback">
                <div className="space-y-3">
                  {round?.events.length ? round.events.map((event) => (
                    <article className="event" key={event.turn}>
                      <div className="flex items-center justify-between">
                        <strong>Turn {event.turn}</strong>
                        <span className={event.points >= 0 ? "points up" : "points down"}>
                          {event.points >= 0 ? `+${event.points}` : event.points}
                        </span>
                      </div>
                      <p>{event.note}</p>
                    </article>
                  )) : <p className="text-sm leading-6 text-[#687387]">Backend move events will appear here.</p>}
                </div>
              </Panel>

              <Panel title="Debrief">
                {debrief ? (
                  <div className="space-y-3 text-sm leading-6 text-[#4d5869]">
                    <p className="font-mono text-3xl font-semibold text-[#151922]">{debrief.score}/100</p>
                    <p>{debrief.headline}</p>
                    <p><strong>Turning point:</strong> {debrief.turning_point}</p>
                    <p><strong>Next drill:</strong> {debrief.next_run_focus}</p>
                  </div>
                ) : (
                  <p className="text-sm leading-6 text-[#687387]">End the backend round to see coaching notes.</p>
                )}
              </Panel>
            </aside>
          </div>
        </section>
      </section>
    </main>
  );
}

function toError(error: unknown) {
  return error instanceof Error ? error.message : "Unknown voice backend error.";
}
