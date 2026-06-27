import { useEffect, useRef } from "react";
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
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const inputDisabled = openingLoading || roundComplete;
  const sendDisabled = inputDisabled || audioStatus === "generating" || !input.trim().replace(/…$/, "");

  const statusText = roundComplete
    ? "Round complete"
    : `Gemini Live · ${language === "de" ? "Deutsch" : "English"} · ${audioStatus === "idle" ? "ready" : audioStatus}`;
  const statusDot =
    audioStatus === "speaking"
      ? "bg-emerald-400"
      : audioStatus === "generating"
      ? "bg-amber-400 animate-pulse"
      : "bg-gray-600";

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.scrollTop = textarea.scrollHeight;
  }, [input]);

  return (
    <div className="absolute inset-x-0 bottom-0 pointer-events-none">
      <div className="h-6 bg-gray-950" />
      <div className="bg-gray-950 pb-4 pt-1 px-4 sm:px-6">
        <div className="mx-auto w-full max-w-3xl pointer-events-auto space-y-2">
          {audioError && (
            <div className="text-xs px-3 py-2 rounded-xl bg-rose-950/40 border border-rose-800/50 text-rose-200">
              {audioError}
            </div>
          )}
          {openingError && hasMessages && (
            <div className="text-xs px-3 py-2 rounded-xl bg-rose-950/40 border border-rose-800/50 text-rose-200">
              {openingError}
            </div>
          )}

          <div
            className={`flex items-end gap-2 rounded-[1.75rem] bg-gray-900 border p-2 shadow-2xl shadow-black/40 transition-colors ${
              voiceActive ? "border-rose-500/70" : "border-gray-700 focus-within:border-indigo-500/70"
            }`}
          >
            {voiceSupported && (
              <button
                onClick={onToggleVoice}
                title={voiceActive ? "Stop listening" : "Start voice input"}
                disabled={inputDisabled}
                className={`grid place-items-center w-11 h-11 shrink-0 rounded-full transition-all disabled:opacity-40 ${
                  voiceActive
                    ? "bg-rose-500 text-white shadow-lg shadow-rose-900/40 animate-pulse"
                    : "text-gray-400 hover:text-gray-100 hover:bg-gray-800"
                }`}
              >
                <MicIcon />
              </button>
            )}

            <textarea
              ref={textareaRef}
              className="flex-1 resize-none bg-transparent px-2 py-2.5 text-[15px] leading-relaxed focus:outline-none placeholder:text-gray-600 max-h-44"
              rows={1}
              placeholder={
                roundComplete
                  ? "Round complete — open the debrief"
                  : voiceActive
                  ? "Listening… speak your argument"
                  : "Make your argument…"
              }
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={onKeyDown}
              disabled={inputDisabled}
            />

            <button
              className="grid place-items-center w-11 h-11 shrink-0 rounded-full bg-indigo-600 text-white shadow-lg shadow-indigo-900/40 hover:bg-indigo-500 disabled:opacity-30 transition-all"
              onClick={onSend}
              disabled={sendDisabled}
              title="Send (Enter)"
            >
              <SendIcon />
            </button>
          </div>

          <div className="flex items-center justify-center gap-1.5 text-[11px] text-gray-600">
            <span className={`w-1.5 h-1.5 rounded-full ${statusDot}`} />
            <span>{statusText}</span>
            {!voiceSupported && <span className="text-gray-700">· voice unavailable</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

function MicIcon() {
  return (
    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="19" x2="12" y2="22" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 2 11 13" />
      <path d="M22 2 15 22l-4-9-9-4 20-7z" />
    </svg>
  );
}
