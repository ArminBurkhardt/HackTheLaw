import { RefObject } from "react";
import { classificationLabel, MOVE_COLOR, MOVE_ICON } from "./labels";
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
    <div className="flex-1 min-h-0 overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl px-4 sm:px-6 pt-6 pb-40 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center text-center pt-24">
            <p className="text-gray-200 text-base font-semibold tracking-tight">
              {openingLoading ? "Opponent is opening the negotiation…" : "Opening turn unavailable."}
            </p>
            <p className="text-gray-500 text-sm mt-2 max-w-sm leading-relaxed">
              {openingError ?? "Anchor first. The opponent will not wait — and will not fold to confidence."}
            </p>
          </div>
        )}

        {messages.map((message, index) => {
          const isUser = message.role === "user";
          const move = message.moveEvent;
          return (
            <div key={index} className={`flex flex-col gap-1.5 ${isUser ? "items-end" : "items-start"}`}>
              <div
                className={`max-w-[88%] px-4 py-3 text-[15px] leading-relaxed whitespace-pre-wrap ${
                  isUser
                    ? "user-message-bubble bg-indigo-600 text-white rounded-3xl rounded-tr-lg"
                    : "bg-gray-800 text-gray-100 rounded-3xl rounded-tl-lg border border-gray-700"
                }`}
              >
                {message.text}
              </div>

              {isUser && move && (
                <div className="flex items-center gap-2 px-1">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-800 border border-gray-700 pl-1 pr-2.5 py-1">
                    <img
                      src={MOVE_ICON[move.classification]}
                      alt={classificationLabel(move.classification)}
                      title={classificationLabel(move.classification)}
                      className="w-4 h-4 shrink-0"
                    />
                    <span className={`text-xs font-semibold capitalize ${MOVE_COLOR[move.classification]}`}>
                      {classificationLabel(move.classification)}
                    </span>
                  </span>
                  <span className="text-xs text-gray-600 tabular-nums">
                    {move.position_delta > 0 ? "+" : ""}
                    {move.position_delta.toFixed(2)}
                  </span>
                </div>
              )}

              {isUser && move && showDetails && (
                <div className="max-w-[88%] rounded-xl bg-gray-900 border border-gray-800 px-3 py-2 text-xs text-gray-400 leading-relaxed">
                  {move.refs.length > 0 && (
                    <span className="text-gray-500">{move.refs.join(", ")} — </span>
                  )}
                  {move.note}
                </div>
              )}
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
