import { useId } from "react";

/**
 * Two overlapping rings with the shared part filled: a person and the assistant working
 * together. Decorative; the wordmark next to it names the product.
 */
export function Logo({ className = "logo" }: { className?: string }) {
  const clipId = `logo-clip-${useId().replace(/[^A-Za-z0-9_-]/g, "")}`;
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">
      <defs>
        <clipPath id={clipId}>
          <circle cx="9" cy="12" r="7" />
        </clipPath>
      </defs>
      <circle cx="15" cy="12" r="7" fill="currentColor" clipPath={`url(#${clipId})`} />
      <circle cx="9" cy="12" r="7" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="15" cy="12" r="7" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}
