"use client";

import { cn } from "@/lib/utils";
import type { ComponentProps } from "react";

export type CodeBlockProps = ComponentProps<"div"> & {
  code: string;
  language?: string;
};

export function CodeBlock({ className, code, language = "text", ...props }: CodeBlockProps) {
  return (
    <div className={cn("overflow-hidden rounded-md border bg-muted/50", className)} {...props}>
      <div className="border-b px-3 py-2 font-mono text-xs text-muted-foreground">
        {language}
      </div>
      <pre className="overflow-x-auto p-3 text-xs leading-5">
        <code>{code}</code>
      </pre>
    </div>
  );
}
