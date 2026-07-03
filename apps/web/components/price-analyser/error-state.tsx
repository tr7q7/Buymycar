"use client"

import { AlertTriangle, RotateCcw } from "lucide-react"
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"

interface ErrorStateProps {
  message: string
  onRetry: () => void
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col gap-4">
      <Alert variant="destructive">
        <AlertTriangle />
        <AlertTitle>Une erreur est survenue</AlertTitle>
        <AlertDescription>{message}</AlertDescription>
      </Alert>
      <Button onClick={onRetry} className="w-full" variant="outline">
        <RotateCcw data-icon="inline-start" />
        Réessayer
      </Button>
    </div>
  )
}
