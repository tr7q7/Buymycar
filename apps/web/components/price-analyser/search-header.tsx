import { CarFront } from "lucide-react"

export function SearchHeader() {
  return (
    <header className="flex flex-col items-center gap-3 text-center">
      <div className="flex size-12 items-center justify-center rounded-2xl border border-border bg-card shadow-sm">
        <CarFront className="size-6 text-primary" aria-hidden="true" />
      </div>
      <div className="flex flex-col gap-1">
        <h1 className="text-balance text-xl font-semibold tracking-tight sm:text-2xl">
          AutoCote
        </h1>
        <p className="text-pretty text-sm text-muted-foreground">
          La cote en temps réel du marché de l'occasion
        </p>
      </div>
    </header>
  )
}
