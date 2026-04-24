import type { SVGProps } from "react";

interface SpecialAgentIconProps extends SVGProps<SVGSVGElement> {
  /** Override the icon color (defaults to currentColor). */
  color?: string;
}

/**
 * Bot/robot icon for agents. Drawn in the Heroicons v2 outline style to match
 * the sibling nav icons (Plan, Marketplace).
 */
export function SpecialAgentIcon({ className, color, ...rest }: SpecialAgentIconProps) {
  const tint = color ?? "currentColor";
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke={tint}
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden
      {...rest}
    >
      <path d="M12 4v2.5" />
      <circle cx="12" cy="3.1" r="0.9" fill={tint} stroke="none" />
      <rect x="4.5" y="6.5" width="15" height="13" rx="2.5" />
      <path d="M3 12v3" />
      <path d="M21 12v3" />
      <circle cx="9.5" cy="12.5" r="1" fill={tint} stroke="none" />
      <circle cx="14.5" cy="12.5" r="1" fill={tint} stroke="none" />
      <path d="M10 16.25h4" />
    </svg>
  );
}
