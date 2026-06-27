import { RefObject } from "react";
import { classificationLabel, MOVE_COLOR, MOVE_EMOJI } from "./labels";
import type { Message } from "./types";

interface Props {
  messages: Message[];
  showDetails: boolean;
  openingLoading: boolean;
  openingError: string | null;
  bottomRef: RefObject<HTMLDivElement>;
}

export default function MessageList({ messages, showDetails, openingLoading, openingError, bottomRef }: Props) {
  return (
    <div className="flex-1 bg-gray-900 border border-gray-700 rounded-xl p-4 overflow-y-auto space-y-3">
      {messages.length === 0 && (
        <div className="h-full flex flex-col items-center justify-center text-center px-6">
          <div className="text-3xl mb-3">⚔️</div>
          <p className="text-gray-300 text-sm font-medium">
            {openingLoading ? "Opponent is opening the negotiation..." : "Opening turn unavailable."}
          </p>
          <p className="text-gray-600 text-xs mt-1.5 max-w-xs">
            {openingError ?? "Anchor first. The opponent will not wait and will not fold to confidence."}
          </p>
        </div>
      )}
      {messages.map((message, index) => (
        <div key={index} className={`flex flex-col ${message.role === "user" ? "items-end" : "items-start"}`}>
          <div
            className={`max-w-[78%] rounded-2xl px-4 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
              message.role === "user"
                ? "bg-indigo-600 text-white rounded-br-sm"
                : "bg-gray-800 border border-gray-700 text-gray-100 rounded-bl-sm"
            }`}
          >
            {message.text}
          </div>
          {message.role === "user" && message.moveEvent && (
            <div className="mt-1 flex items-center gap-1.5 text-xs">
              <span title={classificationLabel(message.moveEvent.classification)} className="text-base leading-none">
                {MOVE_EMOJI[message.moveEvent.classification]}
              </span>
              <span className={`font-medium ${MOVE_COLOR[message.moveEvent.classification]}`}>
                {classificationLabel(message.moveEvent.classification)}
              </span>
              <span className="text-gray-600">
                Δ{message.moveEvent.position_delta > 0 ? "+" : ""}
                {message.moveEvent.position_delta.toFixed(2)}
              </span>
              {showDetails && (
                <>
                  {message.moveEvent.refs.length > 0 && (
                    <span className="text-gray-600">({message.moveEvent.refs.join(", ")})</span>
                  )}
                  <span className="text-gray-600 italic">— {message.moveEvent.note}</span>
                </>
              )}
            </div>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
