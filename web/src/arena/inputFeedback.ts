export type LingSignal = "citation" | "assertive" | "hedging" | "conceding" | "neutral";

export interface LingFeedback {
  signal: LingSignal;
  emoji: string;
  label: string;
  color: string;
}

export function analyzeInput(text: string): LingFeedback | null {
  if (!text.trim()) return null;

  if (/\b(art\.|article\s+\d|gdpr|regulation|directive|recital|pursuant|celex|28\(|83\(|32\()/i.test(text)) {
    return { signal: "citation", emoji: "⚖️", label: "Legal citation — strong", color: "text-indigo-400" };
  }

  if (/\b(i agree|you'?re right|that'?s fair|i accept|i concede|fine by me|we can accept|happy to agree|i'?ll accept)\b/i.test(text)) {
    return { signal: "conceding", emoji: "🚨", label: "Concession language", color: "text-rose-400" };
  }

  if (/\b(i think|maybe|perhaps|i'?m not sure|might|we could consider|possibly|i suppose|sort of|kind of|i feel like|could argue)\b/i.test(text)) {
    return { signal: "hedging", emoji: "⚠️", label: "Hedging detected", color: "text-amber-400" };
  }

  if (/\b(must|require|mandate|insist|demand|non-negotiable|our position is|we require|not acceptable|reject|this is essential)\b/i.test(text)) {
    return { signal: "assertive", emoji: "💪", label: "Assertive stance", color: "text-emerald-400" };
  }

  return { signal: "neutral", emoji: "✍️", label: "Composing…", color: "text-gray-500" };
}
