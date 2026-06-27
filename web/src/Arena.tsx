import { useState, useEffect, useRef, useCallback } from "react";
import { createRoundWs, MoveEvent } from "./lib/ws";

interface Message {
  role: "user" | "opponent";
  text: string;
  moveEvent?: MoveEvent;
}

interface Props {
  roundId: string;
  onRoundEnd: (roundId: string) => void;
}

function classificationColor(c: MoveEvent["classification"]): string {
  switch (c) {
    case "good_move": return "text-emerald-400";
    case "held_firm": return "text-blue-400";
    case "conceded_early": return "text-rose-400";
    case "missed_point": return "text-amber-400";
    case "overplayed": return "text-orange-400";
    default: return "text-gray-500";
  }
}

function classificationLabel(c: MoveEvent["classification"]): string {
  return c.replace("_", " ");
}

// Tension meter: maps current_position to a visual bar.
// Position is running sum of position_deltas; clamp to [-5, 5] for display.
function TensionMeter({ position }: { position: number }) {
  const clamped = Math.max(-5, Math.min(5, position));
  // Map [-5,5] → [0%,100%]; center at 50%
  const pct = ((clamped + 5) / 10) * 100;
  const color =
    clamped > 1 ? "bg-emerald-500" :
    clamped < -1 ? "bg-rose-500" :
    "bg-amber-400";

  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>Their ground</span>
        <span>Neutral</span>
        <span>Your ground</span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden relative">
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-px h-full bg-gray-600" />
        </div>
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function Arena({ roundId, onRoundEnd }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [position, setPosition] = useState(0);
  const [showDetails, setShowDetails] = useState(false);
  const wsRef = useRef<ReturnType<typeof createRoundWs> | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ws = createRoundWs(
      roundId,
      (msg) => {
        setMessages((prev) => [
          ...prev,
          { role: "opponent", text: msg.reply, moveEvent: msg.move_event },
        ]);
        if (msg.current_position !== undefined) {
          setPosition(msg.current_position);
        }
        setConnected(true);
      },
      () => setConnected(false)
    );
    wsRef.current = ws;
    setConnected(true);
    return () => ws.close();
  }, [roundId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(() => {
    const text = input.trim();
    if (!text || !wsRef.current) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    wsRef.current.send(text);
    setInput("");
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto p-4">
      {/* Header */}
      <div className="mb-4 space-y-2">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold tracking-tight">Crucible Arena</h1>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-red-500"}`} />
            <span className="text-sm text-gray-400">{connected ? "Live" : "Disconnected"}</span>
            <button
              className="ml-2 text-xs text-gray-500 hover:text-gray-300 underline underline-offset-2"
              onClick={() => setShowDetails((v) => !v)}
            >
              {showDetails ? "Hide details" : "Show details"}
            </button>
            <button
              className="ml-2 px-3 py-1 text-sm bg-gray-700 rounded hover:bg-gray-600"
              onClick={() => onRoundEnd(roundId)}
            >
              End round
            </button>
          </div>
        </div>
        <TensionMeter position={position} />
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {messages.length === 0 && (
          <p className="text-gray-500 text-sm mt-8 text-center">
            Make your opening argument to begin.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}>
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-indigo-600 text-white rounded-br-sm"
                  : "bg-gray-800 text-gray-100 rounded-bl-sm"
              }`}
            >
              {m.text}
            </div>
            {/* Details drawer: MoveEvent for user turns */}
            {showDetails && m.role === "user" && m.moveEvent && (
              <div className="mt-1 max-w-[75%] text-xs text-gray-500 space-y-0.5">
                <span className={`font-medium ${classificationColor(m.moveEvent.classification)}`}>
                  {classificationLabel(m.moveEvent.classification)}
                </span>
                {" · "}
                <span>Δ{m.moveEvent.position_delta > 0 ? "+" : ""}{m.moveEvent.position_delta.toFixed(2)}</span>
                {m.moveEvent.refs.length > 0 && (
                  <span className="ml-1 text-gray-600">({m.moveEvent.refs.join(", ")})</span>
                )}
                <div className="text-gray-600 italic">{m.moveEvent.note}</div>
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="mt-4 flex gap-2">
        <textarea
          className="flex-1 resize-none rounded-xl bg-gray-800 border border-gray-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          rows={2}
          placeholder="Your argument..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          className="px-4 py-2 bg-indigo-600 rounded-xl hover:bg-indigo-500 disabled:opacity-40 self-end"
          onClick={sendMessage}
          disabled={!input.trim() || !connected}
        >
          Send
        </button>
      </div>
    </div>
  );
}
