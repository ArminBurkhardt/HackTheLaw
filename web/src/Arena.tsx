import { useCallback, useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import ContextRail from "./ContextRail";
import Composer from "./arena/Composer";
import MessageList from "./arena/MessageList";
import TensionMeter from "./arena/TensionMeter";
import { applyContextUpdate } from "./arena/contextUpdates";
import { PERSONA_LABELS, SCENARIO_LABELS } from "./arena/labels";
import { collectSpeechDraft, composeSpeechInput, silenceAndStopRecognition } from "./arena/speechInput";
import type { ArenaProps, AudioStatus, Message } from "./arena/types";
import {
  audioBlobFromBase64,
  fetchOpeningLiveTurn,
  fetchRoundContext,
  RoundContext,
  sendLiveTurn,
} from "./lib/ws";

const SpeechRecognitionAPI =
  typeof window !== "undefined"
    ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    : null;

const voiceSupported = !!SpeechRecognitionAPI;

export default function Arena({ roundId, language, onRoundEnd }: ArenaProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [position, setPosition] = useState(0);
  const [showDetails, setShowDetails] = useState(false);
  const [roundContext, setRoundContext] = useState<RoundContext | null>(null);
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

  const loadContext = useCallback(async () => {
    setContextLoading(true);
    setContextError(null);
    try {
      const context = await fetchRoundContext(roundId);
      setRoundContext(context);
      setPosition(context.current_position);
      setRoundComplete(Boolean(context.round_complete));
      setMessages((prev) => applyContextUpdate(prev, context));
    } catch (error) {
      setContextError(error instanceof Error ? error.message : String(error));
    } finally {
      setContextLoading(false);
    }
  }, [roundId]);

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
    void loadContext();
  }, [loadContext]);

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
  const canEndRound = !openingLoading && audioStatus === "idle" && messages.some((message) => message.role === "user") && !roundComplete;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="w-full px-4 lg:px-8 py-4 lg:py-6 lg:grid lg:grid-cols-[minmax(0,1fr)_22rem] gap-6">
        <div className="flex flex-col h-[calc(100vh-2rem)] lg:h-[calc(100vh-3rem)] min-w-0">
          <div className="mb-5 flex items-center justify-between gap-4">
            <div className="text-xs uppercase tracking-widest text-gray-500 truncate">
              Arena
              {scenarioLabel && <span className="text-gray-400"> · {scenarioLabel}</span>}
              {personaLabel && <span className="text-indigo-400"> · {personaLabel}</span>}
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span className="flex items-center gap-1.5 text-xs text-gray-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                Live
              </span>
              <button
                className="px-3.5 py-2 text-xs font-semibold bg-gray-800 border border-gray-600 rounded-lg text-gray-200 hover:border-gray-400 hover:bg-gray-700 transition-colors"
                onClick={() => setShowDetails((v) => !v)}
              >
                {showDetails ? "Hide details" : "Details"}
              </button>
              <button
                className="px-4 py-2 text-xs font-semibold bg-rose-600 rounded-lg text-white shadow-lg shadow-rose-900/30 hover:bg-rose-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                onClick={() => onRoundEnd(roundId)}
                disabled={!canEndRound}
              >
                End round
              </button>
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-4">
            <div className="flex items-baseline justify-between mb-4">
              <h1 className="text-2xl font-bold tracking-tight">Crucible Arena</h1>
              <span className="text-xs text-gray-500">
                {openingLoading ? "Opening" : `Turn ${messages.filter((m) => m.role === "user").length}`}
              </span>
            </div>
            <TensionMeter position={position} />
          </div>

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

function removePendingUserMessage(messages: Message[], text: string): Message[] {
  const next = [...messages];
  const last = next[next.length - 1];
  if (last?.role === "user" && last.text === text && !last.moveEvent) next.pop();
  return next;
}
