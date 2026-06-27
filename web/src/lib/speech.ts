export type SpeechRecognitionLike = {
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

export function hasSpeechRecognition(): boolean {
  return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
}

export function createSpeechRecognition(): SpeechRecognitionLike | null {
  const Recognition = window.SpeechRecognition ?? window.webkitSpeechRecognition;
  return Recognition ? new Recognition() : null;
}

export function hasAudioPlayback(): boolean {
  return typeof window !== "undefined" && "Audio" in window && "URL" in window;
}

export function cancelAudio(audio: HTMLAudioElement | null) {
  if (!audio) return;
  audio.pause();
  audio.currentTime = 0;
}

export function playAudioBlob(
  blob: Blob,
  existingAudio: HTMLAudioElement | null,
  callbacks: {
    onEnd?: () => void;
    onError?: () => void;
    onStart?: () => void;
  } = {},
): HTMLAudioElement | null {
  if (!hasAudioPlayback()) return null;

  cancelAudio(existingAudio);
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  audio.onplay = () => callbacks.onStart?.();
  audio.onended = () => {
    URL.revokeObjectURL(url);
    callbacks.onEnd?.();
  };
  audio.onerror = () => {
    URL.revokeObjectURL(url);
    callbacks.onError?.();
  };
  void audio.play().catch(() => {
    URL.revokeObjectURL(url);
    callbacks.onError?.();
  });

  return audio;
}
