import { type AnchorHTMLAttributes, forwardRef } from "react";
import { cn } from "./utils";

export interface ButtonLinkProps
  extends AnchorHTMLAttributes<HTMLAnchorElement> {
  variant?: "default" | "outline" | "ghost" | "link";
  size?: "default" | "sm";
}

const ButtonLink = forwardRef<HTMLAnchorElement, ButtonLinkProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    return (
      <a
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950",
          variant === "default" &&
            "bg-blue-900 text-white font-semibold hover:bg-blue-800",
          variant === "outline" &&
            "border border-slate-200 bg-white hover:bg-slate-100 text-slate-900",
          variant === "ghost" && "hover:bg-slate-100 text-slate-900",
          variant === "link" &&
            "text-slate-900 underline-offset-4 hover:underline",
          size === "default" && "h-10 px-4 py-2",
          size === "sm" && "h-8 px-3 text-xs",
          className
        )}
        {...props}
      />
    );
  }
);
ButtonLink.displayName = "ButtonLink";

export { ButtonLink };
