import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva("ux-button", {
  variants:{variant:{default:"ux-button-primary",secondary:"ux-button-secondary",ghost:"ux-button-ghost",segment:"ux-button-segment"},size:{default:"px-4 py-2",sm:"px-3",lg:"px-8 py-3"}},
  defaultVariants:{variant:"default",size:"default"}
});

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
