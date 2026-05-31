import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

/**
 * MedFlow button. Variants ported from doctorwebsite/medflow's
 * .mf-btn-primary / .mf-btn-secondary / .mf-icon-btn idioms (44px min
 * height, 2px ink border, focus-ring on the accent token).
 */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors " +
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] " +
    "focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed " +
    "min-h-[44px]",
  {
    variants: {
      variant: {
        primary:
          "bg-primary text-primary-foreground border-2 border-mf-ink hover:opacity-90",
        secondary:
          "bg-card text-foreground border-2 border-mf-ink hover:bg-mf-paper-2",
        ghost: "bg-transparent text-foreground hover:bg-mf-paper-2",
        link: "bg-transparent text-accent underline-offset-2 hover:underline min-h-0",
        destructive:
          "bg-destructive text-destructive-foreground border-2 border-destructive hover:opacity-90",
      },
      size: {
        sm: "h-9 px-3 text-sm min-h-[36px]",
        md: "px-5 py-2 text-sm",
        lg: "px-6 py-3 text-base",
        icon: "h-11 w-11 p-0",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, type = "button", ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
);
Button.displayName = "Button";

export { buttonVariants };
