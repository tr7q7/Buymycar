"use client"

import { AnimatePresence, motion } from "motion/react"

import { useCredits } from "@/lib/credits-store"

/**
 * Compteur de crédits, visible en haut de l'application.
 * Style « points/argent de jeu » : pastille verte lisible. Se met à jour à
 * l'initialisation de l'email, après une recherche, un achat et le retour Stripe.
 */
export function CreditCounter() {
  const { credits, justPaid } = useCredits()

  if (credits == null) return null

  const label = `${credits} analyse${credits > 1 ? "s" : ""} restante${
    credits > 1 ? "s" : ""
  }`

  return (
    <div className="flex flex-col items-center gap-2">
      <div
        className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-sm font-semibold text-emerald-700 shadow-sm tabular-nums dark:text-emerald-400"
        aria-live="polite"
      >
        <span className="relative flex size-2.5">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-500/60" />
          <span className="relative inline-flex size-2.5 rounded-full bg-emerald-500" />
        </span>
        {label}
      </div>

      <AnimatePresence>
        {justPaid && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-400"
          >
            ✓ 10 analyses ajoutées
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
