"use client";

import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { Message, MessageContent, MessageResponse } from "@/components/ai-elements/message";
import { Source, Sources, SourcesContent, SourcesTrigger } from "@/components/ai-elements/sources";
import { Tool, ToolContent, ToolHeader, ToolInput, ToolOutput } from "@/components/ai-elements/tool";
import type { DynamicToolUIPart, SourceUrlUIPart, UIMessage } from "ai";

type ChatTranscriptProps = {
  messages: UIMessage[];
  emptyTitle: string;
  emptyDescription: string;
};

export function ChatTranscript({ messages, emptyTitle, emptyDescription }: ChatTranscriptProps) {
  return (
    <Conversation className="min-h-0">
      <ConversationContent className="gap-5 p-0">
        {messages.length === 0 ? (
          <ConversationEmptyState title={emptyTitle} description={emptyDescription} />
        ) : (
          messages.map((message) => <TranscriptMessage key={message.id} message={message} />)
        )}
      </ConversationContent>
      <ConversationScrollButton />
    </Conversation>
  );
}

function TranscriptMessage({ message }: { message: UIMessage }) {
  const sourceParts = message.parts.filter(isSourceUrlPart);

  return (
    <Message from={message.role}>
      <MessageContent>
        {message.parts.map((part, index) => {
          if (part.type === "text") {
            return <MessageResponse key={`${message.id}-text-${index}`}>{part.text}</MessageResponse>;
          }

          if (part.type === "dynamic-tool") {
            return <ToolPart key={part.toolCallId} part={part} />;
          }

          return null;
        })}
        {sourceParts.length ? <SourceList sources={sourceParts} /> : null}
      </MessageContent>
    </Message>
  );
}

function ToolPart({ part }: { part: DynamicToolUIPart }) {
  const input = "input" in part ? part.input : undefined;
  const output = "output" in part ? part.output : undefined;
  const errorText = "errorText" in part ? part.errorText : undefined;

  return (
    <Tool defaultOpen={part.state === "output-error"}>
      <ToolHeader type="dynamic-tool" state={part.state} toolName={part.toolName} title={part.title} />
      <ToolContent>
        {input === undefined ? null : <ToolInput input={input} />}
        <ToolOutput output={output} errorText={errorText} />
      </ToolContent>
    </Tool>
  );
}

function SourceList({ sources }: { sources: SourceUrlUIPart[] }) {
  return (
    <Sources defaultOpen>
      <SourcesTrigger count={sources.length} />
      <SourcesContent>
        {sources.map((source) => (
          <Source href={source.url} key={source.sourceId} title={source.title ?? source.url} />
        ))}
      </SourcesContent>
    </Sources>
  );
}

function isSourceUrlPart(part: UIMessage["parts"][number]): part is SourceUrlUIPart {
  return part.type === "source-url";
}
