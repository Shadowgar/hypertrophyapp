import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-[transform,box-shadow,background-color,border-color] duration-150 ease-out focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "border border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white shadow-[var(--ui-depth-shadow-2)] hover:shadow-[var(--ui-glow-active),var(--ui-depth-shadow-3)]",
        secondary:
          "material-module text-white hover:border-[var(--ui-edge-active)] hover:bg-[var(--ui-accent-idle)]",
        ghost:
          "border border-transparent bg-transparent text-white hover:border-[var(--ui-edge-idle)] hover:bg-[color-mix(in_srgb,var(--ui-surface-1)_54%,transparent)]",
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
