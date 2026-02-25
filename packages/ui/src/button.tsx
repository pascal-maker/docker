import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "./utils";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost" | "link";
  size?: "default" | "sm";
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { className, variant = "default", size = "default", style, ...props },
    ref
  ) => {
    const isInverted = className?.includes("bg-white");
    const forceWhiteText =
      variant === "default" && !isInverted;
    const mergedStyle = forceWhiteText
      ? { color: "white", ...style }
      : style;
    const defaultVariantClass =
      variant === "default" &&
      cn(
        "bg-blue-900 font-semibold hover:bg-blue-800",
        !isInverted && "!text-white"
      );
    return (
      <button
        ref={ref}
        style={mergedStyle}
        className={cn(
          "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 disabled:pointer-events-none disabled:opacity-50",
          defaultVariantClass,
          variant === "outline" &&
            "border border-slate-200 bg-white hover:bg-slate-100",
          variant === "ghost" && "hover:bg-slate-100",
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
Button.displayName = "Button";

export { Button };
