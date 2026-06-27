import type { RadarAxis } from "./RadarChart";

export interface ScenarioDef {
  id: string;
  label: string;
  description: string;
  available: boolean;
}

export interface PersonaDef {
  id: string;
  label: string;
  description: string;
  available: boolean;
  radar: RadarAxis[];
  tagline: string;
}

export interface HardnessDef {
  id: string;
  label: string;
  description: string;
  effect: string;
}

export interface BriefEntry {
  title: string;
  pinpoint: string;
  note: string;
}

export interface ScenarioBrief {
  authorities: BriefEntry[];
  strategy: string[];
  watchOut: string[];
}

export const SCENARIOS: ScenarioDef[] = [
  {
    id: "negotiation",
    label: "SaaS Liability Negotiation",
    description: "Negotiate liability caps and exclusions in a business-critical software licence.",
    available: true,
  },
  {
    id: "hot_seat",
    label: "Hot Seat",
    description: "Defend your position under rapid-fire cross-examination.",
    available: false,
  },
  {
    id: "difficult_client",
    label: "Difficult Client",
    description: "Advise an unreasonable client who resists your guidance.",
    available: false,
  },
];

export const PERSONAS: PersonaDef[] = [
  {
    id: "aggressor",
    label: "The Aggressor",
    description: "Deadline-obsessed, ultimatum-prone, exploits every hesitation.",
    tagline: "High pressure. Zero patience. Every pause is a weakness.",
    available: true,
    radar: [
      { label: "Aggression", value: 0.9 },
      { label: "Pressure", value: 0.9 },
      { label: "Verbosity", value: 0.6 },
      { label: "Tempo", value: 0.8 },
      { label: "Flexibility", value: 0.2 },
    ],
  },
  {
    id: "charmer",
    label: "The Charmer",
    description: "Warm and collegial - dangerous because you lower your guard.",
    tagline: "Friendly fire. False consensus. The compliment is the trap.",
    available: true,
    radar: [
      { label: "Aggression", value: 0.3 },
      { label: "Pressure", value: 0.4 },
      { label: "Verbosity", value: 0.8 },
      { label: "Tempo", value: 0.5 },
      { label: "Flexibility", value: 0.5 },
    ],
  },
  {
    id: "stonewaller",
    label: "The Stonewaller",
    description: "Monosyllabic and immovable. Waits you out.",
    tagline: "Silence is strategy. They will outlast you.",
    available: true,
    radar: [
      { label: "Aggression", value: 0.5 },
      { label: "Pressure", value: 0.6 },
      { label: "Verbosity", value: 0.3 },
      { label: "Tempo", value: 0.2 },
      { label: "Flexibility", value: 0.1 },
    ],
  },
  {
    id: "technician",
    label: "The Technician",
    description: "Buries you in clause numbers and recital references.",
    tagline: "Chapter-and-verse arguments only. Vague citations crumble.",
    available: true,
    radar: [
      { label: "Aggression", value: 0.4 },
      { label: "Pressure", value: 0.5 },
      { label: "Verbosity", value: 0.9 },
      { label: "Tempo", value: 0.6 },
      { label: "Flexibility", value: 0.4 },
    ],
  },
];

export const HARDNESS_LEVELS: HardnessDef[] = [
  {
    id: "guided",
    label: "Guided",
    description: "Provider counsel still resists, but gives clearer commercial reasoning.",
    effect: "Best for first runs: the AI asks clarifying questions before escalating deal risk.",
  },
  {
    id: "standard",
    label: "Standard",
    description: "Balanced sparring on the playbook as written.",
    effect: "The AI moves only for concrete legal or commercial substance.",
  },
  {
    id: "hard",
    label: "Hard",
    description: "Strict ladder, stricter pushback, less credit for vague arguments.",
    effect: "The AI requires precise trade-offs, fallback discipline, and carve-out reasoning.",
  },
];

export const SCENARIO_BRIEFS: Record<string, ScenarioBrief> = {
  negotiation: {
    authorities: [
      { title: "BGB Sec. 307", pinpoint: "Sec. 307", note: "Unfair standard terms control against one-sided SaaS risk allocation" },
      { title: "BGB Sec. 309 No. 7", pinpoint: "Sec. 309 No. 7", note: "Keep injury, intent, and gross-negligence liability outside blanket exclusions" },
      { title: "BGB Sec. 276(3)", pinpoint: "Sec. 276(3)", note: "Intentional liability cannot be waived in advance" },
      { title: "Market standard", pinpoint: "SaaS caps", note: "1x annual fees is provider-friendly; higher caps need economic justification" },
      { title: "Insurance proof", pinpoint: "Risk pricing", note: "A lower cap needs reciprocal value such as coverage, SLA, scope, or price" },
    ],
    strategy: [
      "Anchor first: 1-2x annual fees plus explicit carve-outs for fraud, intent, gross negligence, and security/privacy incidents.",
      "Ask why the provider's 1x cap is enough for business-critical software; make them justify the allocation.",
      "Concede only for value: SLA reduction, proof of insurance, price reduction, service scope, or narrower damage categories.",
      "Separate legal carve-outs from ordinary commercial loss. Unlimited liability across everything is the walk-away trap.",
    ],
    watchOut: [
      "Accepting the 1x annual-fee cap immediately without extracting a trade-off.",
      "Blanket exclusions that silently cover intent, gross negligence, fraud, or security/privacy failures.",
      "Pushing unlimited liability so broadly that the provider credibly walks away.",
    ],
  },
};
