import { useCallback, useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import ContextRail from "./ContextRail";
import Composer from "./arena/Composer";
import MessageList from "./arena/MessageList";
import StandingBar from "./arena/TensionMeter";
import { applyContextUpdate } from "./arena/contextUpdates";
import { PERSONA_LABELS, SCENARIO_LABELS } from "./arena/labels";
import { collectSpeechDraft, composeSpeechInput, silenceAndStopRecognition } from "./arena/speechInput";
import type { ArenaProps, AudioStatus, Message } from "./arena/types";
import {
  audioBlobFromBase64,
  fetchOpeningLiveTurn,
  fetchRoundContext,
  sendLiveTurn,
} from "./lib/ws";
import type { RoundContext } from "./lib/ws";

const SpeechRecognitionAPI =
  typeof window !== "undefined"
    ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    : null;

const voiceSupported = !!SpeechRecognitionAPI;

export default function Arena({
  roundId,
  initialContext = null,
  initialContextPromise = null,
  language,
  onRoundEnd,
}: ArenaProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [position, setPosition] = useState(0);
  const [winProbability, setWinProbability] = useState<number | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [showContext, setShowContext] = useState(false); // mobile drawer
  const [roundContext, setRoundContext] = useState<RoundContext | null>(initialContext);
  const [contextError, setContextError] = useState<string | null>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [openingLoading, setOpeningLoading] = useState(true);
  const [openingError, setOpeningError] = useState<string | null>(null);
  const [voiceActive, setVoiceActive] = useState(false);
  const [audioStatus, setAudioStatus] = useState<AudioStatus>("idle");
  const [audioError, setAudioError] = useState<string | null>(null);
  const [roundComplete, setRoundComplete] = useState(false);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
  const speechBaseInputRef = useRef("");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const applyRoundContext = useCallback((context: NonNullable<ArenaProps["initialContext"]>) => {
    setRoundContext(context);
    setPosition(context.current_position);
    setRoundComplete(Boolean(context.round_complete));
    setMessages((prev) => applyContextUpdate(prev, context));
  }, []);

  const loadContext = useCallback(async () => {
    setContextLoading(true);
    setContextError(null);
    try {
      const context = await fetchRoundContext(roundId);
      setRoundContext(context);
      setPosition(context.current_position);
      setWinProbability(
        typeof context.win_probability === "number" ? context.win_probability : null
      );
      setRoundComplete(Boolean(context.round_complete));
      setMessages((prev) => applyContextUpdate(prev, context));
    } catch (error) {
      setContextError(error instanceof Error ? error.message : String(error));
    } finally {
      setContextLoading(false);
    }
  }, [applyRoundContext, roundId]);

  const playLiveAudio = useCallback(async (audio: Blob) => {
    if (typeof window === "undefined") return;
    try {
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
    } catch (error) {
      setAudioStatus("idle");
      setAudioError(error instanceof Error ? error.message : String(error));
    }
  }, []);

  const stopVoiceInput = useCallback(() => {
    silenceAndStopRecognition(recognitionRef.current);
    recognitionRef.current = null;
    speechBaseInputRef.current = "";
    setVoiceActive(false);
  }, []);

  useEffect(() => {
    return () => {
      silenceAndStopRecognition(recognitionRef.current);
      audioRef.current?.pause();
    };
  }, []);

  useEffect(() => {
    let active = true;
    if (initialContext) {
      applyRoundContext(initialContext);
      return () => {
        active = false;
      };
    }
    if (initialContextPromise) {
      setContextLoading(true);
      setContextError(null);
      void initialContextPromise
        .then((context) => {
          if (active && context) applyRoundContext(context);
        })
        .catch((error) => {
          if (active) setContextError(error instanceof Error ? error.message : String(error));
        })
        .finally(() => {
          if (active) setContextLoading(false);
        });
      return () => {
        active = false;
      };
    }
    void loadContext();
    return () => {
      active = false;
    };
  }, [applyRoundContext, initialContext, initialContextPromise, loadContext]);

  useEffect(() => {
    let active = true;
    setOpeningLoading(true);
    setOpeningError(null);
    setAudioError(null);
    setRoundComplete(false);
    setAudioStatus("generating");
    fetchOpeningLiveTurn(roundId, language)
      .then((payload) => {
        if (!active) return;
        setMessages([{ role: "opponent", text: payload.reply }]);
        void playLiveAudio(audioBlobFromBase64(payload.audio_base64, payload.mime_type));
        void loadContext();
      })
      .catch((error) => {
        if (!active) return;
        setAudioStatus("idle");
        setOpeningError(error instanceof Error ? error.message : String(error));
      })
      .finally(() => {
        if (active) setOpeningLoading(false);
      });
    return () => {
      active = false;
    };
  }, [language, loadContext, playLiveAudio, roundId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(() => {
    if (roundComplete) return;
    const text = input.trim();
    if (!text) return;

    stopVoiceInput();
    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");

    setAudioError(null);
    setAudioStatus("generating");
    void sendLiveTurn(roundId, text, language)
      .then((msg) => {
        setMessages((prev) => {
          const next = [...prev];
          const reply = msg.transcript || msg.reply;
          const appended: Message[] = reply ? [...next, { role: "opponent", text: reply }] : next;
          return appended;
        });
        void playLiveAudio(audioBlobFromBase64(msg.audio_base64, msg.mime_type));
        window.setTimeout(() => void loadContext(), 400);
        window.setTimeout(() => void loadContext(), 1200);
      })
      .catch((error) => {
        setAudioStatus("idle");
        setMessages((prev) => removePendingUserMessage(prev, text));
        setAudioError(error instanceof Error ? error.message : String(error));
      });
  }, [input, language, loadContext, playLiveAudio, roundComplete, roundId, stopVoiceInput]);

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  const toggleVoice = useCallback(() => {
    if (!voiceSupported) return;
    if (voiceActive) {
      stopVoiceInput();
      return;
    }

    const recognition = new SpeechRecognitionAPI();
    speechBaseInputRef.current = input;
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = language === "de" ? "de-DE" : "en-GB";
    recognition.onresult = (event: any) => {
      setInput(composeSpeechInput(speechBaseInputRef.current, collectSpeechDraft(event.results)));
    };
    recognition.onerror = () => {
      recognitionRef.current = null;
      speechBaseInputRef.current = "";
      setVoiceActive(false);
    };
    recognition.onend = () => {
      recognitionRef.current = null;
      speechBaseInputRef.current = "";
      setVoiceActive(false);
    };
    recognition.start();
    recognitionRef.current = recognition;
    setVoiceActive(true);
  }, [input, language, stopVoiceInput, voiceActive]);

  const scenarioLabel = roundContext
    ? SCENARIO_LABELS[roundContext.scenario] ?? roundContext.scenario
    : null;
  const personaLabel = roundContext
    ? PERSONA_LABELS[roundContext.persona] ?? roundContext.persona
    : null;
  const personaInitial = personaLabel ? personaLabel.replace(/^The\s+/i, "").charAt(0).toUpperCase() : "•";
  const turnCount = messages.filter((m) => m.role === "user").length;
  const canEndRound = !openingLoading && audioStatus === "idle" && turnCount > 0 && !roundComplete;

  return (
    <div className="fixed inset-0 flex flex-col bg-gray-950 text-gray-100">
      {/* ═══ Command bar ════════════════════════════════════════════ */}
      <header className="flex items-center gap-4 h-[68px] px-4 sm:px-6 border-b border-gray-800 bg-gray-900">
        {/* Left — opponent identity */}
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="relative shrink-0">
            <div className="grid place-items-center w-11 h-11 rounded-2xl bg-indigo-600 text-white font-bold text-lg shadow-lg shadow-indigo-900/40">
              {personaInitial}
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full bg-emerald-400 ring-2 ring-gray-900 animate-pulse" />
          </div>
          <div className="min-w-0">
            <div className="text-[15px] font-semibold tracking-tight leading-tight truncate">
              {personaLabel ?? "Crucible Arena"}
            </div>
            <div className="text-xs text-gray-500 truncate">
              {scenarioLabel ?? "Loading scenario…"}
              <span className="mx-1.5 text-gray-700">•</span>
              {openingLoading ? "Opening" : `Turn ${turnCount}`}
            </div>
          </div>
        </div>

        {/* Center — current standing (the focal point) */}
        <div className="hidden md:block w-72 lg:w-96 shrink-0">
          <StandingBar position={position} winProbability={winProbability} />
        </div>

        {/* Right — actions */}
        <div className="flex items-center justify-end gap-2 flex-1">
          <button
            onClick={() => setShowDetails((v) => !v)}
            title="Toggle move annotations"
            className={`group flex items-center gap-2 h-9 px-3.5 rounded-full text-xs font-medium border transition-all ${
              showDetails
                ? "bg-indigo-500/15 border-indigo-500/50 text-indigo-300"
                : "bg-transparent border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-500"
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full transition-colors ${showDetails ? "bg-indigo-400" : "bg-gray-600 group-hover:bg-gray-400"}`} />
            Annotations
          </button>
          <button
            onClick={() => setShowContext(true)}
            className="lg:hidden grid place-items-center w-9 h-9 rounded-full border border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-500 transition-colors"
            title="Show context"
          >
            <PanelIcon />
          </button>
          <button
            onClick={() => onRoundEnd(roundId)}
            disabled={!canEndRound}
            className="flex items-center gap-2 h-9 pl-3.5 pr-4 rounded-full text-xs font-semibold text-rose-300 bg-rose-500/10 border border-rose-500/40 hover:bg-rose-500 hover:text-white hover:border-rose-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            <StopIcon />
            End round
          </button>
        </div>
      </header>

      {/* Mobile standing strip */}
      <div className="md:hidden px-4 py-2.5 border-b border-gray-800 bg-gray-900">
        <StandingBar position={position} winProbability={winProbability} />
      </div>

      {/* ═══ Body ═══════════════════════════════════════════════════ */}
      <div className="flex-1 flex min-h-0">
        {/* Conversation stream — full bleed */}
        <main className="relative flex-1 min-w-0 flex flex-col">
          <MessageList
            messages={messages}
            showDetails={showDetails}
            openingLoading={openingLoading}
            openingError={openingError}
            bottomRef={bottomRef}
          />
          <Composer
            input={input}
            setInput={setInput}
            onKeyDown={handleKeyDown}
            onSend={sendMessage}
            onToggleVoice={toggleVoice}
            voiceActive={voiceActive}
            voiceSupported={voiceSupported}
            openingLoading={openingLoading}
            audioStatus={audioStatus}
            audioError={audioError}
            openingError={openingError}
            hasMessages={messages.length > 0}
            language={language}
            roundComplete={roundComplete}
          />
        </main>

        {/* Right rail — desktop */}
        <div className="hidden lg:block w-[340px] xl:w-[380px] shrink-0">
          <ContextRail
            context={roundContext}
            error={contextError}
            loading={contextLoading}
            onRefresh={() => void loadContext()}
          />
        </div>
      </div>

      {/* Context drawer — mobile/tablet */}
      {showContext && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="flex-1 bg-black/60 backdrop-blur-sm" onClick={() => setShowContext(false)} />
          <div className="w-[88%] max-w-sm h-full animate-[slidein_0.2s_ease-out]">
            <ContextRail
              context={roundContext}
              error={contextError}
              loading={contextLoading}
              onRefresh={() => void loadContext()}
              onClose={() => setShowContext(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function StopIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  );
}

function PanelIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <line x1="15" y1="4" x2="15" y2="20" />
    </svg>
  );
}

function removePendingUserMessage(messages: Message[], text: string): Message[] {
  const next = [...messages];
  const last = next[next.length - 1];
  if (last?.role === "user" && last.text === text && !last.moveEvent) next.pop();
  return next;
}
