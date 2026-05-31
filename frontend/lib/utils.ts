import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merges Tailwind class names with conflict-aware deduping. Matches the
 * shadcn/medflow convention so component snippets ported from the wireframe
 * (`className={cn(base, conditional && "...")}`) work without modification.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
