"use client"

import { CheckCircle2, ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"

interface DoneStateProps {
  count: number
  onViewResults: () => void
  onNewSearch: () => void
}

export function DoneState({
  count,
  onViewResults,
  onNewSearch,
}: DoneStateProps) {
  return (
    <div className="flex flex-col items-center gap-6 py-4 text-center">
      <div className="flex size-14 items-center justify-center rounded-2xl bg-emerald-500/10">
        <CheckCircle2
          className="size-7 text-emerald-600 dark:text-emerald-500"
          aria-hidden="true"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <p className="text-balance text-sm font-medium">Analyse terminée</p>
        <p className="text-pretty text-sm text-muted-foreground">
          {count} annonce{count > 1 ? "s" : ""} retenue{count > 1 ? "s" : ""}
        </p>
      </div>

      <div className="flex w-full flex-col gap-2">
        <Button onClick={onViewResults} className="w-full">
          Voir les résultats
          <ArrowRight data-icon="inline-end" />
        </Button>
        <Button onClick={onNewSearch} variant="ghost" className="w-full">
          Nouvelle analyse
        </Button>
      </div>
    </div>
  )
}
