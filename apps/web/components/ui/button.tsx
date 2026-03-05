import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-[transform,opacity] duration-150 ease-out hover:-translate-y-[1px] active:translate-y-px focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--ui-edge-active)] disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "border border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white shadow-[var(--ui-depth-shadow-2)] hover:bg-[rgba(220,38,38,0.25)] hover:shadow-[var(--ui-glow-active),var(--ui-depth-shadow-3)]",
        secondary:
          "material-module text-white hover:border-[var(--ui-edge-active)] hover:bg-[var(--ui-accent-idle)] hover:shadow-[var(--ui-depth-shadow-3)]",
        ghost:
          "border border-transparent bg-transparent text-white hover:border-[var(--ui-edge-idle)] hover:bg-[color-mix(in_srgb,var(--ui-surface-1)_54%,transparent)]",
        segment:
          "border border-[var(--ui-edge-idle)] bg-[color-mix(in_srgb,var(--ui-surface-1)_72%,transparent)] text-zinc-200 shadow-[var(--ui-depth-shadow-1)] hover:border-[var(--ui-edge-hover)] hover:text-zinc-100 aria-pressed:border-[var(--ui-edge-active)] aria-pressed:bg-[var(--ui-accent-active)] aria-pressed:text-white aria-pressed:shadow-[var(--ui-glow-active),var(--ui-depth-shadow-2)]",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return <button className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
