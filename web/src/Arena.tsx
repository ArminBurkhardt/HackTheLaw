import { useCallback, useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import ContextRail from "./ContextRail";
import Composer from "./arena/Composer";
import MessageList from "./arena/MessageList";
import TensionMeter from "./arena/TensionMeter";
import { PERSONA_LABELS, SCENARIO_LABELS } from "./arena/labels";
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

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadContext = useCallback(async () => {
    setContextLoading(true);
    setContextError(null);
    try {
      setRoundContext(await fetchRoundContext(roundId));
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

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
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
    const text = input.trim();
    if (!text) return;

    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    if (voiceActive) {
      recognitionRef.current?.stop();
      setVoiceActive(false);
    }

    setAudioError(null);
    setAudioStatus("generating");
    void sendLiveTurn(roundId, text, language)
      .then((msg) => {
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
          return [...next, { role: "opponent", text: msg.transcript || msg.reply }];
        });
        if (msg.current_position !== undefined) setPosition(msg.current_position);
        void playLiveAudio(audioBlobFromBase64(msg.audio_base64, msg.mime_type));
        void loadContext();
      })
      .catch((error) => {
        setAudioStatus("idle");
        setMessages((prev) => removePendingUserMessage(prev, text));
        setAudioError(error instanceof Error ? error.message : String(error));
      });
  }, [input, language, loadContext, playLiveAudio, roundId, voiceActive]);

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  const toggleVoice = useCallback(() => {
    if (!voiceSupported) return;
    if (voiceActive) {
      recognitionRef.current?.stop();
      setVoiceActive(false);
      return;
    }

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = language === "de" ? "de-DE" : "en-GB";
    recognition.onresult = (event: any) => {
      let interim = "";
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) final += transcript;
        else interim += transcript;
      }
      setInput((prev) => (final ? prev + final : prev.replace(/…$/, "") + interim + "…"));
    };
    recognition.onerror = () => setVoiceActive(false);
    recognition.onend = () => setVoiceActive(false);
    recognition.start();
    recognitionRef.current = recognition;
    setVoiceActive(true);
  }, [language, voiceActive]);

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
          <div className="mb-5 flex items-center justify-between gap-4">
            <div className="text-xs uppercase tracking-widest text-gray-500 truncate">
              Arena
              {scenarioLabel && <span className="text-gray-400"> · {scenarioLabel}</span>}
              {personaLabel && <span className="text-indigo-400"> · {personaLabel}</span>}
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span className="flex items-center gap-1.5 text-xs text-gray-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                Live
              </span>
              <button className="text-xs text-gray-400 hover:text-gray-200" onClick={() => setShowDetails((v) => !v)}>
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
