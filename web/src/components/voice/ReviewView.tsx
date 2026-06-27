import { MessageSquare, Plus } from "lucide-react";

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
          <button
            aria-label="Back to chat"
            className="secondary-button compact icon-button"
            onClick={onBackToChat}
            title="Back to chat"
            type="button"
          >
            <MessageSquare aria-hidden="true" size={17} />
          </button>
          <button
            aria-label="Start new session"
            className="primary-button compact icon-button"
            onClick={onNewSession}
            title="Start new session"
            type="button"
          >
            <Plus aria-hidden="true" size={17} />
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
          <h2>Argument review</h2>
          <div className="argument-list">
            {debrief.argument_reviews.length ? debrief.argument_reviews.map((item) => (
              <article className="argument-row" key={`${item.turn}-${item.verdict}`}>
                <div>
                  <strong>Turn {item.turn}</strong>
                  <span>{item.verdict}</span>
                </div>
                <blockquote>{item.quote}</blockquote>
                <p>{item.feedback}</p>
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
