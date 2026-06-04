import Link from "next/link"
import { cn } from "@/lib/utils"
import { MfLogoMark } from "@/components/auth/LogoMark"

type BrandSize = "sm" | "md" | "lg"

const TEXT_SIZE: Record<BrandSize, string> = {
  sm: "text-lg",
  md: "text-xl",
  lg: "text-[28px]",
}

interface BrandLogoProps {
  href?: string
  size?: BrandSize
  showWordmark?: boolean
  /** e.g. "hidden lg:inline" to collapse wordmark on narrow sidebars */
  wordmarkClassName?: string
  className?: string
}

export function BrandLogo({
  href,
  size = "sm",
  showWordmark = true,
  wordmarkClassName,
  className,
}: BrandLogoProps) {
  const lockup = (
    <span
      className={cn(
        "mf-brand-lockup inline-flex min-h-[44px] items-center gap-2.5",
        className
      )}
    >
      <MfLogoMark size={size} />
      {showWordmark && (
        <span
          className={cn(
            "mf-display font-semibold leading-none tracking-tight text-[var(--mf-ink)]",
            TEXT_SIZE[size],
            wordmarkClassName
          )}
        >
          MedFlow
        </span>
      )}
    </span>
  )

  if (href) {
    return (
      <Link
        href={href}
        className="rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mf-accent)]"
        aria-label="MedFlow home"
      >
        {lockup}
      </Link>
    )
  }

  return lockup
}
