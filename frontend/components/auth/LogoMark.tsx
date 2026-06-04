import { cn } from "@/lib/utils"

const LOGO_SIZES = {
  sm: 28,
  md: 36,
  lg: 40,
} as const

type LogoSize = keyof typeof LOGO_SIZES

function MedFlowMarkIcon({ size }: { size: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className="block"
    >
      <rect width="32" height="32" rx="8" fill="var(--mf-accent)" />
      <path
        d="M5 16 H9.5 Q10.5 16 11 14.5 Q11.5 13 12.5 16 L14.5 10 L16.5 22 L18.5 14 Q19.5 11 20.5 16 L23 16 H27"
        stroke="white"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

interface LogoMarkProps {
  size?: number | LogoSize
  className?: string
}

export function MfLogoMark({ size = "sm", className }: LogoMarkProps) {
  const px = typeof size === "number" ? size : LOGO_SIZES[size]
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center leading-none",
        className
      )}
    >
      <MedFlowMarkIcon size={px} />
    </span>
  )
}

/** @deprecated Use MfLogoMark */
export const LogoMark = MfLogoMark
