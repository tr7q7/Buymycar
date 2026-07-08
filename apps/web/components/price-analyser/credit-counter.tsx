"use client"

import { AnimatePresence, motion } from "motion/react"

import { useCredits } from "@/lib/credits-store"

/**
 * Compteur de crédits, visible en haut de l'application.
 * Style « points/argent de jeu » : pastille verte lisible. Se met à jour à
 * l'initialisation de l'email, après une recherche, un achat et le retour Stripe.
 */
export function CreditCounter() {
  const { credits, justPaid, paymentConfirming } = useCredits()

  const n = credits ?? 0
  const label = `${n} analyse${n > 1 ? "s" : ""} restante${n > 1 ? "s" : ""}`

  return (
    <div className="flex flex-col items-center gap-2">
      {credits != null && (
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
      )}

      <AnimatePresence>
        {paymentConfirming ? (
          <motion.div
            key="confirming"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-400"
          >
            Paiement confirmé, mise à jour des crédits…
          </motion.div>
        ) : (
          justPaid && (
            <motion.div
              key="paid"
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              className="rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-400"
            >
              ✓ Paiement confirmé, crédits mis à jour
            </motion.div>
          )
        )}
      </AnimatePresence>
    </div>
  )
}
