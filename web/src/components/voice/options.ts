import type { VoiceDifficulty, VoiceLanguage, VoicePersona } from "@/lib/voiceBackend";

export const personas: { id: VoicePersona; label: string; detail: string }[] = [
  { id: "difficult_client", label: "Difficult client", detail: "Pressure, deadlines, commercial pushback" },
  { id: "impatient_partner", label: "Impatient partner", detail: "Fast refusals and terse follow-ups" },
  { id: "regulator", label: "Regulator", detail: "Clause precision and legal authority" },
];

export const difficulties: { id: VoiceDifficulty; label: string; detail: string }[] = [
  { id: "warmup", label: "Warmup", detail: "Slower pace, lower consequence" },
  { id: "live", label: "Live", detail: "Realistic partner-level exchange" },
  { id: "crossfire", label: "Crossfire", detail: "Hard mode with sharper pushback" },
];

export const languages: { id: VoiceLanguage; label: string; detail: string }[] = [
  { id: "en", label: "English", detail: "Common-law negotiation language" },
  { id: "de", label: "Deutsch", detail: "Deutsche Verhandlungssprache" },
];

export function optionLabel<T extends string>(items: { id: T; label: string }[], id: T) {
  return items.find((item) => item.id === id)?.label ?? id;
}
