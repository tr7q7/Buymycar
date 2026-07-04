import { cn } from "@/lib/utils"
import { scoreMeta } from "@/lib/format"

interface ScoreBadgeProps {
  score: number | null | undefined
  className?: string
  /** Show the numeric score alongside the label. */
  showValue?: boolean
}

export function ScoreBadge({ score, className, showValue }: ScoreBadgeProps) {
  const meta = scoreMeta(score)
  const hasScore = score != null && Number.isFinite(score)

  return (
    <span
      className={cn(
        "inline-flex w-fit items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        meta.tintClass,
        className,
      )}
    >
      <span className={cn("size-1.5 shrink-0 rounded-full", meta.dotClass)} />
      {meta.label}
      {showValue && hasScore ? (
        <span className="tabular-nums opacity-70">{Math.round(score!)}</span>
      ) : null}
    </span>
  )
}
