import type { HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-sm px-2 py-0.5 font-mono text-xs font-medium uppercase tracking-wide",
  {
    variants: {
      tone: {
        default: "bg-surface text-muted",
        ok: "bg-ok/15 text-ok",
        error: "bg-error/15 text-error",
        warn: "bg-warn/15 text-warn",
        accent: "bg-accent/15 text-accent",
        fetch: "bg-surface text-muted",
      },
    },
    defaultVariants: { tone: "default" },
  },
);

export function Badge({
  className,
  tone,
  ...props
}: HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
