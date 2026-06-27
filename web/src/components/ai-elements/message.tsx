"use client";

import { cn } from "@/lib/utils";
import { cjk } from "@streamdown/cjk";
import { code } from "@streamdown/code";
import { math } from "@streamdown/math";
import { mermaid } from "@streamdown/mermaid";
import type { UIMessage } from "ai";
import { memo, type ComponentProps, type HTMLAttributes } from "react";
import { Streamdown } from "streamdown";

export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: UIMessage["role"];
};

export function Message({ className, from, ...props }: MessageProps) {
  return (
    <article
      className={cn(
        "group flex w-full max-w-[95%] flex-col gap-2",
        from === "user" ? "ml-auto items-end" : "items-start",
        className,
      )}
      data-role={from}
      {...props}
    />
  );
}

export type MessageContentProps = HTMLAttributes<HTMLDivElement>;

export function MessageContent({ className, ...props }: MessageContentProps) {
  return (
    <div
      className={cn(
        "min-w-0 max-w-full rounded-md text-sm leading-6",
        "group-data-[role=user]:bg-secondary group-data-[role=user]:px-4 group-data-[role=user]:py-3",
        "group-data-[role=assistant]:text-foreground",
        className,
      )}
      {...props}
    />
  );
}

export type MessageResponseProps = ComponentProps<typeof Streamdown>;

const streamdownPlugins = { cjk, code, math, mermaid };

export const MessageResponse = memo(function MessageResponse({
  className,
  ...props
}: MessageResponseProps) {
  return (
    <Streamdown
      className={cn("prose prose-sm max-w-none dark:prose-invert", className)}
      plugins={streamdownPlugins}
      {...props}
    />
  );
});
