export interface WsMessage {
  reply: string;
}

export type WsHandler = (msg: WsMessage) => void;
export type WsErrorHandler = (err: Event) => void;

export function createRoundWs(
  roundId: string,
  onMessage: WsHandler,
  onError?: WsErrorHandler
): { send: (text: string) => void; close: () => void } {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${window.location.host}/round/${roundId}/turn`);

  ws.onmessage = (e) => {
    try {
      onMessage(JSON.parse(e.data) as WsMessage);
    } catch {
      // ignore malformed frames
    }
  };

  if (onError) ws.onerror = onError;

  return {
    send: (text: string) => ws.send(JSON.stringify({ message: text })),
    close: () => ws.close(),
  };
}
