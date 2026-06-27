interface SpeechLikeResult {
  readonly isFinal: boolean;
  readonly [index: number]: { readonly transcript: string } | undefined;
}

interface SpeechLikeResultList {
  readonly length: number;
  readonly [index: number]: SpeechLikeResult | undefined;
}

export interface SpeechDraft {
  finalText: string;
  interimText: string;
}

export function collectSpeechDraft(results: SpeechLikeResultList): SpeechDraft {
  const finalParts: string[] = [];
  const interimParts: string[] = [];

  for (let index = 0; index < results.length; index += 1) {
    const result = results[index];
    const transcript = result?.[0]?.transcript.trim();
    if (!result || !transcript) continue;
    if (result.isFinal) finalParts.push(transcript);
    else interimParts.push(transcript);
  }

  return {
    finalText: joinSpeechParts(finalParts),
    interimText: joinSpeechParts(interimParts),
  };
}

export function composeSpeechInput(baseText: string, draft: SpeechDraft): string {
  const spoken = joinSpeechParts([draft.finalText, draft.interimText]);
  if (!spoken) return baseText;

  const separator = baseText.trim() && !/\s$/.test(baseText) ? " " : "";
  return `${baseText}${separator}${spoken}${draft.interimText ? "…" : ""}`;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function silenceAndStopRecognition(recognition: any) {
  if (!recognition) return;
  recognition.onresult = null;
  recognition.onerror = null;
  recognition.onend = null;
  try {
    recognition.stop();
  } catch {
    // Browser speech recognition can throw if already stopped.
  }
}

function joinSpeechParts(parts: string[]): string {
  return parts
    .map((part) => part.trim())
    .filter(Boolean)
    .join(" ")
    .replace(/\s+/g, " ");
}
