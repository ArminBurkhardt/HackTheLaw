import type { KeyboardEvent } from "react";
import type { AudioStatus } from "./types";

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
  roundComplete: boolean;
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
  roundComplete,
}: Props) {
  const inputDisabled = openingLoading || roundComplete;

  return (
    <div className="mt-4 space-y-2">
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
          disabled={inputDisabled}
        />
        {voiceSupported && (
          <button
            onClick={onToggleVoice}
            title={voiceActive ? "Stop listening" : "Start voice input"}
            disabled={inputDisabled}
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
          className="px-6 py-2.5 bg-indigo-600 rounded-xl hover:bg-indigo-500 disabled:opacity-40 self-end text-sm font-semibold text-white shadow-lg shadow-indigo-900/30 transition-colors"
          onClick={onSend}
          disabled={inputDisabled || audioStatus === "generating" || !input.trim().replace(/…$/, "")}
        >
          Send
        </button>
      </div>

      <p className="text-xs text-gray-600 text-center">
        {roundComplete
          ? "Round complete"
          : `Gemini Live (${language === "de" ? "Deutsch" : "English"}): ${audioStatus === "idle" ? "ready" : audioStatus}`}
      </p>

      {!voiceSupported && (
        <p className="text-xs text-gray-600 text-center">Voice input not available in this browser.</p>
      )}
    </div>
  );
}
