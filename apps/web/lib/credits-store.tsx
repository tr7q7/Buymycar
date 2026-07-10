"use client"

import * as React from "react"

import {
  confirmCheckout,
  createCheckoutSession,
  getVisitorId,
  initCredits,
} from "@/lib/api"

const EMAIL_STORAGE_KEY = "autocote_email"
const PAID_FLAG_KEY = "autocote_just_paid"
const SESSION_ID_KEY = "autocote_session_id"

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

  // Retour de Stripe : on crédite d'ABORD via /checkout/confirm (indépendant du
  // webhook, source de vérité côté Stripe), puis on retombe sur un polling de
  // /credits en secours. Ça fonctionne même si le webhook est mal configuré.
  const confirmAfterPayment = React.useCallback(
    async (mail: string, vid: string, sessionId: string) => {
      if (!isValidEmail(mail) && !sessionId) return
      setPaymentConfirming(true)
      try {
        // 1) Confirmation directe via l'API (crédite selon la session Stripe).
        if (sessionId) {
          try {
            const res = await confirmCheckout(sessionId)
            // On aligne le compte affiché sur l'email qui a réellement payé.
            if (res.email) {
              setEmail(res.email)
              window.localStorage.setItem(EMAIL_STORAGE_KEY, res.email)
            }
            if (typeof res.balance === "number") {
              setCredits(res.balance)
              return
            }
          } catch {
            // on bascule sur le polling ci-dessous
          }
        }

        // 2) Polling de secours (si pas de session_id ou confirmation indisponible).
        let baseline: number | null = null
        for (let i = 0; i < 20; i++) {
          try {
            const data = await initCredits(mail, vid)
            setCredits(data.credits_remaining)
            setDeviceBlocked(!!data.device_blocked)
            if (baseline === null) {
              baseline = data.credits_remaining
              if (baseline > 0) return
            } else if (data.credits_remaining > baseline) {
              return
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
    const sessionId = params.get("session_id")
    // Flags sessionStorage : robustes au double-montage StrictMode + nettoyage d'URL.
    const paidFlag = window.sessionStorage.getItem(PAID_FLAG_KEY) === "1"
    if (isSuccess) {
      window.sessionStorage.setItem(PAID_FLAG_KEY, "1")
      if (sessionId) window.sessionStorage.setItem(SESSION_ID_KEY, sessionId)
      params.delete("payment")
      params.delete("session_id")
      const qs = params.toString()
      window.history.replaceState(
        {},
        "",
        window.location.pathname + (qs ? `?${qs}` : ""),
      )
    }
    const pendingSession =
      sessionId || window.sessionStorage.getItem(SESSION_ID_KEY) || ""
    if (isSuccess || paidFlag) {
      setJustPaid(true)
      void confirmAfterPayment(stored || "", vid, pendingSession)
      window.setTimeout(() => {
        setJustPaid(false)
        window.sessionStorage.removeItem(PAID_FLAG_KEY)
        window.sessionStorage.removeItem(SESSION_ID_KEY)
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
    const normalized = email.trim().toLowerCase()
    // Persiste l'email AVANT de partir vers Stripe : au retour (?payment=success),
    // le compteur interroge exactement l'email qui a payé (et pas un ancien email
    // resté en localStorage) → plus de crédits « invisibles ».
    window.localStorage.setItem(EMAIL_STORAGE_KEY, normalized)
    setBuyError("")
    setCheckoutLoading(true)
    try {
      const { url } = await createCheckoutSession(normalized)
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
