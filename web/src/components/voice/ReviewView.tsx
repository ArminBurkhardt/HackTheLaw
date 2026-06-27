import { ChatTranscript } from "@/components/ai/ChatTranscript";
import { roundConversationMessages } from "@/lib/aiTranscript";
import type { Debrief, RoundState } from "@/lib/voiceBackend";

type ReviewViewProps = {
  debrief: Debrief;
  onBackToChat: () => void;
  onNewSession: () => void;
  round: RoundState;
};

export function ReviewView({ debrief, onBackToChat, onNewSession, round }: ReviewViewProps) {
  return (
    <main className="review-shell">
      <header className="review-header">
        <div>
          <p className="product-mark">Crucible</p>
          <h1>Session review</h1>
        </div>
        <div className="review-actions">
          <button className="secondary-button compact" onClick={onBackToChat} type="button">
            Chat
          </button>
          <button className="primary-button compact" onClick={onNewSession} type="button">
            New session
          </button>
        </div>
      </header>

      <section className="review-body">
        <section className="review-summary">
          <p className="review-score">{debrief.score}/100</p>
          <h2>{debrief.headline}</h2>
          <p>{debrief.next_run_focus}</p>
        </section>

        <section className="review-grid">
          <article className="review-card">
            <h2>Turning point</h2>
            <p>{debrief.turning_point}</p>
          </article>
          <article className="review-card">
            <h2>Stronger move</h2>
            <p>{debrief.stronger_move}</p>
          </article>
        </section>

        <section className="review-card">
          <h2>Move feedback</h2>
          <div className="event-list">
            {round.events.length ? round.events.map((event) => (
              <article className="event-row" key={event.turn}>
                <strong>Turn {event.turn}</strong>
                <span>{event.points >= 0 ? `+${event.points}` : event.points}</span>
                <p>{event.note}</p>
              </article>
            )) : <p>No moves were played.</p>}
          </div>
        </section>

        <section className="review-card">
          <h2>Conversation</h2>
          <ChatTranscript
            messages={roundConversationMessages(round)}
            emptyTitle="No transcript"
            emptyDescription="The round ended without messages."
          />
        </section>
      </section>
    </main>
  );
}
