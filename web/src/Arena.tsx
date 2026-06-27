import { useState, useEffect, useRef, useCallback } from "react";
import ContextRail from "./ContextRail";
import {
  createRoundWs,
  fetchRoundContext,
  MoveEvent,
  RoundContext,
  synthesizeLiveAudio,
} from "./lib/ws";

interface Message {
  role: "user" | "opponent";
  text: string;
  moveEvent?: MoveEvent;
}

interface Props {
  roundId: string;
  language: "en" | "de";
  onRoundEnd: (roundId: string) => void;
}

// ── Display labels (kept in sync with ScenarioPicker) ───────────────────────

const SCENARIO_LABELS: Record<string, string> = {
  negotiation: "SaaS Liability Negotiation",
  hot_seat: "Hot Seat",
  difficult_client: "Difficult Client",
};

const PERSONA_LABELS: Record<string, string> = {
  aggressor: "The Aggressor",
  charmer: "The Charmer",
  stonewaller: "The Stonewaller",
  technician: "The Technician",
};

// ── Move quality display ────────────────────────────────────────────────────

const MOVE_EMOJI: Record<MoveEvent["classification"], string> = {
  good_move: "✅",
  held_firm: "🛡️",
  conceded_early: "🔴",
  missed_point: "❗",
  overplayed: "⚠️",
  neutral: "·",
};

const MOVE_COLOR: Record<MoveEvent["classification"], string> = {
  good_move: "text-emerald-400",
  held_firm: "text-blue-400",
  conceded_early: "text-rose-400",
  missed_point: "text-amber-400",
  overplayed: "text-orange-400",
  neutral: "text-gray-500",
};

function classificationLabel(c: MoveEvent["classification"]): string {
  return c.replace(/_/g, " ");
}

// ── Linguistic pattern analysis ─────────────────────────────────────────────

type LingSignal = "citation" | "assertive" | "hedging" | "conceding" | "neutral";

interface LingFeedback {
  signal: LingSignal;
  emoji: string;
  label: string;
  color: string;
}

function analyzeInput(text: string): LingFeedback | null {
  if (!text.trim()) return null;

  // Citation / legal reference
  if (
    /\b(art\.|article\s+\d|gdpr|regulation|directive|recital|pursuant|celex|28\(|83\(|32\()/i.test(
      text
    )
  ) {
    return { signal: "citation", emoji: "⚖️", label: "Legal citation — strong", color: "text-indigo-400" };
  }

  // Concession language
  if (
    /\b(i agree|you'?re right|that'?s fair|i accept|i concede|fine by me|we can accept|happy to agree|i'?ll accept)\b/i.test(
      text
    )
  ) {
    return { signal: "conceding", emoji: "🚨", label: "Concession language", color: "text-rose-400" };
  }

  // Hedging
  if (
    /\b(i think|maybe|perhaps|i'?m not sure|might|we could consider|possibly|i suppose|sort of|kind of|i feel like|could argue)\b/i.test(
      text
    )
  ) {
    return { signal: "hedging", emoji: "⚠️", label: "Hedging detected", color: "text-amber-400" };
  }

  // Assertive
  if (
    /\b(must|require|mandate|insist|demand|non-negotiable|our position is|we require|not acceptable|reject|this is essential)\b/i.test(
      text
    )
  ) {
    return { signal: "assertive", emoji: "💪", label: "Assertive stance", color: "text-emerald-400" };
  }

  return { signal: "neutral", emoji: "✍️", label: "Composing…", color: "text-gray-500" };
}

// ── Tension meter ───────────────────────────────────────────────────────────

function TensionMeter({ position }: { position: number }) {
  const clamped = Math.max(-5, Math.min(5, position));
  const pct = ((clamped + 5) / 10) * 100;
  const color =
    clamped > 1 ? "bg-emerald-500" : clamped < -1 ? "bg-rose-500" : "bg-amber-400";

  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>Their ground</span>
        <span>Neutral</span>
        <span>Your ground</span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden relative">
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-px h-full bg-gray-600" />
        </div>
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ── Voice support ───────────────────────────────────────────────────────────

const SpeechRecognitionAPI =
  typeof window !== "undefined"
    ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    : null;

const voiceSupported = !!SpeechRecognitionAPI;

// ── Main component ──────────────────────────────────────────────────────────

export default function Arena({ roundId, language, onRoundEnd }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [position, setPosition] = useState(0);
  const [showDetails, setShowDetails] = useState(false);
  const [roundContext, setRoundContext] = useState<RoundContext | null>(null);
  const [contextError, setContextError] = useState<string | null>(null);
  const [contextLoading, setContextLoading] = useState(false);

  // Voice
  const [voiceActive, setVoiceActive] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [audioStatus, setAudioStatus] = useState<"idle" | "preparing" | "speaking">("idle");
  const [audioError, setAudioError] = useState<string | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const wsRef = useRef<ReturnType<typeof createRoundWs> | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Live linguistic feedback
  const lingFeedback = analyzeInput(input);

  const loadContext = useCallback(async () => {
    setContextLoading(true);
    setContextError(null);
    try {
      setRoundContext(await fetchRoundContext(roundId));
    } catch (e) {
      setContextError(e instanceof Error ? e.message : String(e));
    } finally {
      setContextLoading(false);
    }
  }, [roundId]);

  // ── Gemini Live audio helper ──────────────────────────────────────────────
  const speak = useCallback(async (text: string) => {
    if (!ttsEnabled || typeof window === "undefined") return;
    setAudioError(null);
    setAudioStatus("preparing");
    try {
      const audio = await synthesizeLiveAudio(text, language);
      audioRef.current?.pause();
      const url = URL.createObjectURL(audio);
      const nextAudio = new Audio(url);
      nextAudio.onplay = () => setAudioStatus("speaking");
      nextAudio.onended = () => {
        URL.revokeObjectURL(url);
        setAudioStatus("idle");
      };
      nextAudio.onerror = () => {
        URL.revokeObjectURL(url);
        setAudioStatus("idle");
        setAudioError("Gemini Live audio playback failed.");
      };
      audioRef.current = nextAudio;
      await nextAudio.play();
    } catch (e) {
      setAudioStatus("idle");
      setAudioError(e instanceof Error ? e.message : String(e));
    }
  }, [language, ttsEnabled]);

  // ── WebSocket ─────────────────────────────────────────────────────────────
  useEffect(() => {
    let active = true;
    const ws = createRoundWs(
      roundId,
      (msg) => {
        setMessages((prev) => {
          const next = [...prev];
          if (msg.move_event) {
            for (let i = next.length - 1; i >= 0; i -= 1) {
              if (next[i].role === "user" && !next[i].moveEvent) {
                next[i] = { ...next[i], moveEvent: msg.move_event };
                break;
              }
            }
          }
          return [...next, { role: "opponent", text: msg.reply }];
        });
        if (msg.current_position !== undefined) setPosition(msg.current_position);
        setConnected(true);
        void loadContext();
        void speak(msg.reply);
      },
      (isConnected) => {
        if (active) setConnected(isConnected);
      }
    );
    wsRef.current = ws;
    setConnected(true);
    return () => {
      active = false;
      ws.close();
      recognitionRef.current?.stop();
      audioRef.current?.pause();
    };
  }, [loadContext, roundId, speak]);

  useEffect(() => {
    void loadContext();
  }, [loadContext]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Send message ──────────────────────────────────────────────────────────
  const sendMessage = useCallback(() => {
    const text = input.trim();
    if (!text || !wsRef.current) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    wsRef.current.send(text);
    setInput("");
    // Stop voice so interim transcript doesn't keep appending
    if (voiceActive) {
      recognitionRef.current?.stop();
      setVoiceActive(false);
    }
  }, [input, voiceActive]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // ── Voice toggle ──────────────────────────────────────────────────────────
  const toggleVoice = useCallback(() => {
    if (!voiceSupported) return;

    if (voiceActive) {
      recognitionRef.current?.stop();
      setVoiceActive(false);
      return;
    }

    const rec = new SpeechRecognitionAPI();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = language === "de" ? "de-DE" : "en-GB";

    rec.onresult = (event: any) => {
      let interim = "";
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) final += t;
        else interim += t;
      }
      setInput((prev) => (final ? prev + final : prev.replace(/…$/, "") + interim + "…"));
    };

    rec.onerror = () => setVoiceActive(false);
    rec.onend = () => setVoiceActive(false);

    rec.start();
    recognitionRef.current = rec;
    setVoiceActive(true);
  }, [language, voiceActive]);

  // ── Toggle TTS ────────────────────────────────────────────────────────────
  const toggleTts = useCallback(() => {
    setTtsEnabled((v) => {
      if (v) {
        audioRef.current?.pause();
        setAudioStatus("idle");
      }
      return !v;
    });
  }, []);

  const scenarioLabel = roundContext
    ? SCENARIO_LABELS[roundContext.scenario] ?? roundContext.scenario
    : null;
  const personaLabel = roundContext
    ? PERSONA_LABELS[roundContext.persona] ?? roundContext.persona
    : null;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-6xl mx-auto p-4 lg:p-6 lg:grid lg:grid-cols-[minmax(0,1fr)_20rem] gap-6">
        <div className="flex flex-col h-[calc(100vh-2rem)] lg:h-[calc(100vh-3rem)] min-w-0">
          {/* Meta row — mirrors the setup wizard header */}
          <div className="mb-5 flex items-center justify-between gap-4">
            <div className="text-xs uppercase tracking-widest text-gray-500 truncate">
              Arena
              {scenarioLabel && <span className="text-gray-400"> · {scenarioLabel}</span>}
              {personaLabel && <span className="text-indigo-400"> · {personaLabel}</span>}
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span className="flex items-center gap-1.5 text-xs text-gray-400">
                <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-400" : "bg-rose-500"}`} />
                {connected ? "Live" : "Disconnected"}
              </span>
              {/* TTS toggle */}
              <button
                title={ttsEnabled ? "Mute Gemini Live voice" : "Speak opponent replies with Gemini Live"}
                onClick={toggleTts}
                className={`text-base transition-opacity ${ttsEnabled ? "opacity-100" : "opacity-40 hover:opacity-70"}`}
              >
                🔊
              </button>
              <button
                className="text-xs text-gray-400 hover:text-gray-200"
                onClick={() => setShowDetails((v) => !v)}
              >
                {showDetails ? "Hide details" : "Details"}
              </button>
              <button
                className="px-3 py-1.5 text-xs font-medium bg-gray-800 border border-gray-700 rounded-lg hover:border-gray-500 hover:bg-gray-700"
                onClick={() => onRoundEnd(roundId)}
              >
                End round
              </button>
            </div>
          </div>

          {/* Title + tension card */}
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-4">
            <div className="flex items-baseline justify-between mb-4">
              <h1 className="text-2xl font-bold tracking-tight">Crucible Arena</h1>
              <span className="text-xs text-gray-500">
                {messages.length === 0 ? "Awaiting opening" : `Turn ${messages.filter((m) => m.role === "user").length}`}
              </span>
            </div>
            <TensionMeter position={position} />
          </div>

          {/* Message list */}
          <div className="flex-1 bg-gray-900 border border-gray-700 rounded-xl p-4 overflow-y-auto space-y-3">
            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center px-6">
                <div className="text-3xl mb-3">⚔️</div>
                <p className="text-gray-300 text-sm font-medium">Make your opening argument to begin.</p>
                <p className="text-gray-600 text-xs mt-1.5 max-w-xs">
                  Anchor first. Cite chapter and verse. The opponent will not wait — and will not fold to confidence.
                </p>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}>
                <div
                  className={`max-w-[78%] rounded-2xl px-4 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
                    m.role === "user"
                      ? "bg-indigo-600 text-white rounded-br-sm"
                      : "bg-gray-800 border border-gray-700 text-gray-100 rounded-bl-sm"
                  }`}
                >
                  {m.text}
                </div>

                {/* Move quality badge — always visible for user turns */}
                {m.role === "user" && m.moveEvent && (
                  <div className="mt-1 flex items-center gap-1.5 text-xs">
                    <span
                      title={classificationLabel(m.moveEvent.classification)}
                      className="text-base leading-none"
                    >
                      {MOVE_EMOJI[m.moveEvent.classification]}
                    </span>
                    <span className={`font-medium ${MOVE_COLOR[m.moveEvent.classification]}`}>
                      {classificationLabel(m.moveEvent.classification)}
                    </span>
                    <span className="text-gray-600">
                      Δ{m.moveEvent.position_delta > 0 ? "+" : ""}
                      {m.moveEvent.position_delta.toFixed(2)}
                    </span>

                    {/* Expanded details */}
                    {showDetails && (
                      <>
                        {m.moveEvent.refs.length > 0 && (
                          <span className="text-gray-600">
                            ({m.moveEvent.refs.join(", ")})
                          </span>
                        )}
                        <span className="text-gray-600 italic">— {m.moveEvent.note}</span>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Input area */}
          <div className="mt-4 space-y-2">
            {/* Live linguistic feedback banner */}
            {lingFeedback && input.trim() && (
              <div
                className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-800 ${lingFeedback.color}`}
              >
                <span className="text-base leading-none">{lingFeedback.emoji}</span>
                <span className="font-medium">{lingFeedback.label}</span>
                {lingFeedback.signal === "hedging" && (
                  <span className="text-gray-500 ml-auto">
                    Replace hedges with specific legal references
                  </span>
                )}
                {lingFeedback.signal === "conceding" && (
                  <span className="text-gray-500 ml-auto">
                    Are you giving up a must-have?
                  </span>
                )}
                {lingFeedback.signal === "citation" && (
                  <span className="text-gray-500 ml-auto">
                    Good — cite the pinpoint too (Art. X(Y))
                  </span>
                )}
              </div>
            )}

            {audioError && (
              <div className="text-xs px-3 py-1.5 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-200">
                {audioError}
              </div>
            )}

            <div className="flex gap-2 items-end">
              <textarea
                className="flex-1 resize-none rounded-xl bg-gray-800 border border-gray-700 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                rows={2}
                placeholder={voiceActive ? "Listening… speak your argument" : "Your argument…"}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              {/* Mic button */}
              {voiceSupported && (
                <button
                  onClick={toggleVoice}
                  title={voiceActive ? "Stop listening" : "Start voice input"}
                  className={`px-3 py-2.5 rounded-xl text-base transition-all self-end ${
                    voiceActive
                      ? "bg-rose-600 hover:bg-rose-500 animate-pulse"
                      : "bg-gray-800 border border-gray-700 hover:border-gray-500 opacity-70 hover:opacity-100"
                  }`}
                >
                  🎤
                </button>
              )}
              <button
                className="px-5 py-2.5 bg-indigo-600 rounded-xl hover:bg-indigo-500 disabled:opacity-40 self-end text-sm font-semibold"
                onClick={sendMessage}
                disabled={!input.trim().replace(/…$/, "") || !connected}
              >
                Send
              </button>
            </div>

            {ttsEnabled && (
              <p className="text-xs text-gray-600 text-center">
                Gemini Live audio ({language === "de" ? "Deutsch" : "English"}): {audioStatus === "idle" ? "ready" : audioStatus}
              </p>
            )}

            {!voiceSupported && (
              <p className="text-xs text-gray-600 text-center">
                Voice input not available in this browser.
              </p>
            )}
          </div>
        </div>
        <ContextRail
          context={roundContext}
          error={contextError}
          loading={contextLoading}
          onRefresh={() => void loadContext()}
        />
      </div>
    </div>
  );
}
