"use client"

import { motion } from "motion/react"
import { Loader2 } from "lucide-react"

interface LoadingStateProps {
  elapsedMs: number
  onCancel: () => void
}

function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`
}

export function LoadingState({ elapsedMs, onCancel }: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center gap-6 py-4 text-center">
      <div className="flex size-14 items-center justify-center rounded-2xl bg-primary/10">
        <Loader2 className="size-6 animate-spin text-primary" aria-hidden="true" />
      </div>

      <div className="flex flex-col gap-1.5">
        <p className="text-balance text-sm font-medium">
          Analyse du marché en cours…
        </p>
        <p className="text-pretty text-xs text-muted-foreground">
          L&apos;analyse peut prendre 1 à 3 minutes. Vous pouvez laisser cette
          page ouverte.
        </p>
      </div>

      {/* Indeterminate progress bar */}
      <div
        className="relative h-1.5 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-label="Analyse en cours"
      >
        <motion.div
          className="absolute inset-y-0 w-1/3 rounded-full bg-primary"
          animate={{ left: ["-33%", "100%"] }}
          transition={{
            duration: 1.4,
            ease: "easeInOut",
            repeat: Number.POSITIVE_INFINITY,
          }}
        />
      </div>

      <div className="flex flex-col items-center gap-3">
        <span
          className="font-mono text-sm tabular-nums text-muted-foreground"
          aria-live="polite"
        >
          {formatElapsed(elapsedMs)}
        </span>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md text-sm text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          Annuler
        </button>
      </div>
    </div>
  )
}
