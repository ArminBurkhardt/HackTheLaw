import { useState, useEffect, useRef, useCallback } from "react";
import { createRoundWs, MoveEvent } from "./lib/ws";

interface Message {
  role: "user" | "opponent";
  text: string;
  moveEvent?: MoveEvent;
}

interface Props {
  roundId: string;
  onRoundEnd: (roundId: string) => void;
}

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

export default function Arena({ roundId, onRoundEnd }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [position, setPosition] = useState(0);
  const [showDetails, setShowDetails] = useState(false);

  // Voice
  const [voiceActive, setVoiceActive] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);

  const wsRef = useRef<ReturnType<typeof createRoundWs> | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Live linguistic feedback
  const lingFeedback = analyzeInput(input);

  // ── TTS helper ────────────────────────────────────────────────────────────
  const speak = useCallback(
    (text: string) => {
      if (!ttsEnabled || typeof window === "undefined") return;
      window.speechSynthesis.cancel();
      const utt = new SpeechSynthesisUtterance(text);
      utt.lang = "en-GB";
      utt.rate = 0.9;
      window.speechSynthesis.speak(utt);
    },
    [ttsEnabled]
  );

  // ── WebSocket ─────────────────────────────────────────────────────────────
  useEffect(() => {
    const ws = createRoundWs(
      roundId,
      (msg) => {
        setMessages((prev) => [
          ...prev,
          { role: "opponent", text: msg.reply, moveEvent: msg.move_event },
        ]);
        if (msg.current_position !== undefined) setPosition(msg.current_position);
        setConnected(true);
        speak(msg.reply);
      },
      () => setConnected(false)
    );
    wsRef.current = ws;
    setConnected(true);
    return () => {
      ws.close();
      recognitionRef.current?.stop();
      window.speechSynthesis?.cancel();
    };
  }, [roundId, speak]);

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
    rec.lang = "en-GB";

    rec.onresult = (event: SpeechRecognitionEvent) => {
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
  }, [voiceActive]);

  // ── Toggle TTS ────────────────────────────────────────────────────────────
  const toggleTts = useCallback(() => {
    setTtsEnabled((v) => {
      if (v) window.speechSynthesis?.cancel();
      return !v;
    });
  }, []);

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto p-4">
      {/* Header */}
      <div className="mb-4 space-y-2">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold tracking-tight">Crucible Arena</h1>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-red-500"}`} />
            <span className="text-sm text-gray-400">{connected ? "Live" : "Disconnected"}</span>
            {/* TTS toggle */}
            <button
              title={ttsEnabled ? "Mute opponent voice" : "Speak opponent replies aloud"}
              onClick={toggleTts}
              className={`ml-1 text-base transition-opacity ${ttsEnabled ? "opacity-100" : "opacity-40"}`}
            >
              🔊
            </button>
            <button
              className="ml-1 text-xs text-gray-500 hover:text-gray-300 underline underline-offset-2"
              onClick={() => setShowDetails((v) => !v)}
            >
              {showDetails ? "Hide details" : "Details"}
            </button>
            <button
              className="ml-1 px-3 py-1 text-sm bg-gray-700 rounded hover:bg-gray-600"
              onClick={() => onRoundEnd(roundId)}
            >
              End round
            </button>
          </div>
        </div>
        <TensionMeter position={position} />
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {messages.length === 0 && (
          <p className="text-gray-500 text-sm mt-8 text-center">
            Make your opening argument to begin.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}>
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-indigo-600 text-white rounded-br-sm"
                  : "bg-gray-800 text-gray-100 rounded-bl-sm"
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

        <div className="flex gap-2 items-end">
          <textarea
            className="flex-1 resize-none rounded-xl bg-gray-800 border border-gray-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
              className={`px-3 py-2 rounded-xl text-base transition-all self-end ${
                voiceActive
                  ? "bg-rose-600 hover:bg-rose-500 animate-pulse"
                  : "bg-gray-700 hover:bg-gray-600 opacity-70 hover:opacity-100"
              }`}
            >
              🎤
            </button>
          )}
          <button
            className="px-4 py-2 bg-indigo-600 rounded-xl hover:bg-indigo-500 disabled:opacity-40 self-end text-sm font-medium"
            onClick={sendMessage}
            disabled={!input.trim().replace(/…$/, "") || !connected}
          >
            Send
          </button>
        </div>

        {!voiceSupported && (
          <p className="text-xs text-gray-600 text-center">
            Voice input not available in this browser.
          </p>
        )}
      </div>
    </div>
  );
}
