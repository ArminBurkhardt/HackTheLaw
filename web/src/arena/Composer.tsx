import type { KeyboardEvent } from "react";
import type { AudioStatus } from "./types";
import { analyzeInput } from "./inputFeedback";

interface Props {
  input: string;
  setInput: (value: string) => void;
  onKeyDown: (event: KeyboardEvent) => void;
  onSend: () => void;
  onToggleVoice: () => void;
  voiceActive: boolean;
  voiceSupported: boolean;
  openingLoading: boolean;
  audioStatus: AudioStatus;
  audioError: string | null;
  openingError: string | null;
  hasMessages: boolean;
  language: "en" | "de";
}

export default function Composer({
  input,
  setInput,
  onKeyDown,
  onSend,
  onToggleVoice,
  voiceActive,
  voiceSupported,
  openingLoading,
  audioStatus,
  audioError,
  openingError,
  hasMessages,
  language,
}: Props) {
  const feedback = analyzeInput(input);

  return (
    <div className="mt-4 space-y-2">
      {feedback && input.trim() && (
        <div className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-800 ${feedback.color}`}>
          <span className="text-base leading-none">{feedback.emoji}</span>
          <span className="font-medium">{feedback.label}</span>
          {feedback.signal === "hedging" && (
            <span className="text-gray-500 ml-auto">Replace hedges with specific legal references</span>
          )}
          {feedback.signal === "conceding" && (
            <span className="text-gray-500 ml-auto">Are you giving up a must-have?</span>
          )}
          {feedback.signal === "citation" && (
            <span className="text-gray-500 ml-auto">Good — cite the pinpoint too (Art. X(Y))</span>
          )}
        </div>
      )}

      {audioError && (
        <div className="text-xs px-3 py-1.5 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-200">
          {audioError}
        </div>
      )}

      {openingError && hasMessages && (
        <div className="text-xs px-3 py-1.5 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-200">
          {openingError}
        </div>
      )}

      <div className="flex gap-2 items-end">
        <textarea
          className="flex-1 resize-none rounded-xl bg-gray-800 border border-gray-700 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          rows={2}
          placeholder={voiceActive ? "Listening… speak your argument" : "Your argument…"}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={onKeyDown}
          disabled={openingLoading}
        />
        {voiceSupported && (
          <button
            onClick={onToggleVoice}
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
          onClick={onSend}
          disabled={openingLoading || audioStatus === "generating" || !input.trim().replace(/…$/, "")}
        >
          Send
        </button>
      </div>

      <p className="text-xs text-gray-600 text-center">
        Gemini Live ({language === "de" ? "Deutsch" : "English"}): {audioStatus === "idle" ? "ready" : audioStatus}
      </p>

      {!voiceSupported && (
        <p className="text-xs text-gray-600 text-center">Voice input not available in this browser.</p>
      )}
    </div>
  );
}
