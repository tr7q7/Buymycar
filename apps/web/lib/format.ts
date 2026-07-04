const nf = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 })

/** French-style integer grouping, e.g. 50795 -> "50 795". */
export function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return "—"
  return nf.format(Math.round(value))
}

/** French-style price, e.g. 50795 -> "50 795 €". */
export function formatPrice(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—"
  return `${nf.format(Math.round(value))} €`
}

/** French-style mileage, e.g. 120000 -> "120 000 km". */
export function formatMileage(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—"
  return `${nf.format(Math.round(value))} km`
}

export interface ScoreMeta {
  label: string
  /** shadcn Badge variant to use. */
  variant: "default" | "secondary" | "outline" | "destructive"
  /** Tailwind classes for the colored surface (dot / badge tint). */
  dotClass: string
  textClass: string
  tintClass: string
}

/** Maps a 0–100 score (or null) to a label and color treatment. */
export function scoreMeta(score: number | null | undefined): ScoreMeta {
  if (score == null || !Number.isFinite(score)) {
    return {
      label: "—",
      variant: "outline",
      dotClass: "bg-muted-foreground/40",
      textClass: "text-muted-foreground",
      tintClass: "bg-muted text-muted-foreground",
    }
  }
  if (score >= 90) {
    return {
      label: "Excellente affaire",
      variant: "outline",
      dotClass: "bg-emerald-500",
      textClass: "text-emerald-700 dark:text-emerald-400",
      tintClass:
        "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
    }
  }
  if (score >= 75) {
    return {
      label: "Très intéressant",
      variant: "outline",
      dotClass: "bg-green-500",
      textClass: "text-green-700 dark:text-green-400",
      tintClass:
        "bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20",
    }
  }
  if (score >= 55) {
    return {
      label: "Prix correct",
      variant: "outline",
      dotClass: "bg-primary",
      textClass: "text-primary",
      tintClass: "bg-primary/10 text-primary border-primary/20",
    }
  }
  if (score >= 35) {
    return {
      label: "Peu intéressant",
      variant: "outline",
      dotClass: "bg-amber-500",
      textClass: "text-amber-700 dark:text-amber-400",
      tintClass:
        "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
    }
  }
  return {
    label: "Trop cher",
    variant: "outline",
    dotClass: "bg-red-500",
    textClass: "text-red-700 dark:text-red-400",
    tintClass: "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20",
  }
}

export interface ConfidenceMeta {
  dotClass: string
}

/** Colored dot for a confidence label (Élevée / Moyenne / Faible). */
export function confidenceMeta(confidence: string): ConfidenceMeta {
  const c = confidence.trim().toLowerCase()
  if (c.startsWith("élev") || c.startsWith("elev")) {
    return { dotClass: "bg-emerald-500" }
  }
  if (c.startsWith("moy")) {
    return { dotClass: "bg-amber-500" }
  }
  if (c.startsWith("faib")) {
    return { dotClass: "bg-red-500" }
  }
  return { dotClass: "bg-muted-foreground/40" }
}
