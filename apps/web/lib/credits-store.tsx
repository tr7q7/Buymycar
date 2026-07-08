"use client"

import * as React from "react"

import {
  createCheckoutSession,
  getVisitorId,
  initCredits,
} from "@/lib/api"

const EMAIL_STORAGE_KEY = "autocote_email"
const PAID_FLAG_KEY = "autocote_just_paid"

export function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())
}

interface CreditsState {
  email: string
  setEmail: (v: string) => void
  emailValid: boolean
  credits: number | null
  setCredits: React.Dispatch<React.SetStateAction<number | null>>
  deviceBlocked: boolean
  justPaid: boolean
  paymentConfirming: boolean
  visitorId: string
  persistAndLoad: () => void
  buy: () => Promise<void>
  checkoutLoading: boolean
  buyError: string
}

const CreditsContext = React.createContext<CreditsState | null>(null)

export function CreditsProvider({ children }: { children: React.ReactNode }) {
  const [email, setEmail] = React.useState("")
  const [credits, setCredits] = React.useState<number | null>(null)
  const [deviceBlocked, setDeviceBlocked] = React.useState(false)
  const [justPaid, setJustPaid] = React.useState(false)
  const [paymentConfirming, setPaymentConfirming] = React.useState(false)
  const [checkoutLoading, setCheckoutLoading] = React.useState(false)
  const [buyError, setBuyError] = React.useState("")
  const [visitorId, setVisitorId] = React.useState("")

  const emailValid = isValidEmail(email)

  const load = React.useCallback(
    async (mail: string, vid: string) => {
      if (!isValidEmail(mail)) return
      try {
        const data = await initCredits(mail, vid)
        setCredits(data.credits_remaining)
        setDeviceBlocked(!!data.device_blocked)
      } catch {
        // On garde l'état précédent en cas d'indisponibilité réseau.
      }
    },
    [],
  )

  // Retour de Stripe : le webhook qui crédite est ASYNCHRONE (et Render free tier
  // peut démarrer à froid). On interroge donc /credits en boucle jusqu'à voir le
  // solde augmenter, au lieu d'un seul appel qui lirait le solde d'avant crédit.
  const confirmAfterPayment = React.useCallback(
    async (mail: string, vid: string) => {
      if (!isValidEmail(mail)) return
      setPaymentConfirming(true)
      let baseline: number | null = null
      try {
        for (let i = 0; i < 20; i++) {
          try {
            const data = await initCredits(mail, vid)
            setCredits(data.credits_remaining)
            setDeviceBlocked(!!data.device_blocked)
            if (baseline === null) {
              baseline = data.credits_remaining
              if (baseline > 0) return // déjà crédité au 1er appel
            } else if (data.credits_remaining > baseline) {
              return // crédits ajoutés par le webhook
            }
          } catch {
            // on retente
          }
          await new Promise((r) => window.setTimeout(r, 2000))
        }
      } finally {
        setPaymentConfirming(false)
      }
    },
    [],
  )

  // Montage : visitor_id, email mémorisé, retour éventuel de Stripe.
  React.useEffect(() => {
    if (typeof window === "undefined") return
    const vid = getVisitorId()
    setVisitorId(vid)

    const stored = window.localStorage.getItem(EMAIL_STORAGE_KEY)
    if (stored) {
      setEmail(stored)
      void load(stored, vid)
    }

    const params = new URLSearchParams(window.location.search)
    const isSuccess = params.get("payment") === "success"
    // Flag sessionStorage : robuste au double-montage StrictMode (dev).
    const paidFlag = window.sessionStorage.getItem(PAID_FLAG_KEY) === "1"
    if (isSuccess) {
      window.sessionStorage.setItem(PAID_FLAG_KEY, "1")
      params.delete("payment")
      params.delete("session_id")
      const qs = params.toString()
      window.history.replaceState(
        {},
        "",
        window.location.pathname + (qs ? `?${qs}` : ""),
      )
    }
    if (isSuccess || paidFlag) {
      setJustPaid(true)
      if (stored) void confirmAfterPayment(stored, vid)
      window.setTimeout(() => {
        setJustPaid(false)
        window.sessionStorage.removeItem(PAID_FLAG_KEY)
      }, 8000)
    }
  }, [load, confirmAfterPayment])

  const persistAndLoad = React.useCallback(() => {
    if (!emailValid) return
    const normalized = email.trim().toLowerCase()
    window.localStorage.setItem(EMAIL_STORAGE_KEY, normalized)
    void load(normalized, visitorId)
  }, [email, emailValid, visitorId, load])

  const buy = React.useCallback(async () => {
    if (!emailValid) return
    setBuyError("")
    setCheckoutLoading(true)
    try {
      const { url } = await createCheckoutSession(email.trim().toLowerCase())
      window.location.href = url
    } catch {
      setCheckoutLoading(false)
      setBuyError("Paiement momentanément indisponible.")
    }
  }, [email, emailValid])

  const value: CreditsState = {
    email,
    setEmail,
    emailValid,
    credits,
    setCredits,
    deviceBlocked,
    justPaid,
    paymentConfirming,
    visitorId,
    persistAndLoad,
    buy,
    checkoutLoading,
    buyError,
  }

  return (
    <CreditsContext.Provider value={value}>{children}</CreditsContext.Provider>
  )
}

export function useCredits(): CreditsState {
  const ctx = React.useContext(CreditsContext)
  if (!ctx) {
    throw new Error("useCredits doit être utilisé dans <CreditsProvider>")
  }
  return ctx
}
