"use client"

import * as React from "react"
import useSWR from "swr"
import { AnimatePresence, motion } from "motion/react"
import { ArrowRight } from "lucide-react"

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"

import {
  ApiError,
  NeedCreditsError,
  createCheckoutSession,
  fetchBrands,
  fetchFuels,
  fetchJob,
  fetchModels,
  fuelLabel,
  initCredits,
  startSearch,
  type SearchJobResult,
} from "@/lib/api"

import { YearRangeSlider } from "./year-range-slider"
import { LoadingState } from "./loading-state"
import { ErrorState } from "./error-state"
import { DoneState } from "./done-state"
import { ResultsDashboard } from "./results-dashboard"

const POLL_INTERVAL_MS = 2000
const POLL_TIMEOUT_MS = 4 * 60 * 1000
const EMAIL_STORAGE_KEY = "autocote_email"

function isValidEmail(value: string): boolean {
  const v = value.trim()
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)
}

type Status = "idle" | "loading" | "done" | "error" | "results"

interface SearchFormProps {
  onAnalysisComplete?: (result: unknown) => void
  /** Notifies the parent when the full-width results view is shown. */
  onViewChange?: (isResults: boolean) => void
}

const transition = { duration: 0.2, ease: "easeOut" as const }

export function SearchForm({
  onAnalysisComplete,
  onViewChange,
}: SearchFormProps) {
  const currentYear = React.useMemo(() => new Date().getFullYear(), [])

  const [brand, setBrand] = React.useState("")
  const [model, setModel] = React.useState("")
  const [fuel, setFuel] = React.useState("")
  const [years, setYears] = React.useState<[number, number]>([
    2018,
    currentYear,
  ])

  const [status, setStatus] = React.useState<Status>("idle")
  const [errorMessage, setErrorMessage] = React.useState("")
  const [elapsedMs, setElapsedMs] = React.useState(0)
  const [result, setResult] = React.useState<SearchJobResult["result"]>()
  const [submittedQuery, setSubmittedQuery] = React.useState<{
    brand: string
    model: string
    fuel: string
    yearMin: number
    yearMax: number
  }>()

  // --- Email & crédits ---
  const [email, setEmail] = React.useState("")
  const [credits, setCredits] = React.useState<number | null>(null)
  const [checkoutLoading, setCheckoutLoading] = React.useState(false)
  const [buyError, setBuyError] = React.useState("")
  const [justPaid, setJustPaid] = React.useState(false)
  const emailValid = isValidEmail(email)

  // Charge (et crée si besoin) les crédits d'un email. Idempotent côté API.
  const loadCredits = React.useCallback(async (mail: string) => {
    if (!isValidEmail(mail)) return
    try {
      const data = await initCredits(mail)
      setCredits(data.credits_remaining)
    } catch {
      // On garde l'état précédent en cas d'indisponibilité réseau.
    }
  }, [])

  // Au montage : email mémorisé + retour éventuel de Stripe (?payment=success).
  React.useEffect(() => {
    if (typeof window === "undefined") return
    const stored = window.localStorage.getItem(EMAIL_STORAGE_KEY)
    if (stored) {
      setEmail(stored)
      void loadCredits(stored)
    }
    const params = new URLSearchParams(window.location.search)
    const isSuccess = params.get("payment") === "success"
    // Flag sessionStorage : survit au double-montage StrictMode (dev) et à un
    // éventuel nettoyage d'URL antérieur, pour ne pas perdre le message.
    const paidFlag = window.sessionStorage.getItem("autocote_just_paid") === "1"
    if (isSuccess) {
      window.sessionStorage.setItem("autocote_just_paid", "1")
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
      if (stored) void loadCredits(stored)
      window.setTimeout(() => {
        setJustPaid(false)
        window.sessionStorage.removeItem("autocote_just_paid")
      }, 6000)
    }
  }, [loadCredits])

  function handleEmailBlur() {
    if (!emailValid) return
    const normalized = email.trim().toLowerCase()
    window.localStorage.setItem(EMAIL_STORAGE_KEY, normalized)
    void loadCredits(normalized)
  }

  async function handleBuy() {
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
  }

  // Notify the parent so it can widen the layout for the results view.
  React.useEffect(() => {
    onViewChange?.(status === "results")
  }, [status, onViewChange])

  // --- Catalog fetching (SWR, no fetch-in-useEffect) ---
  const {
    data: brands,
    isLoading: brandsLoading,
    error: brandsError,
  } = useSWR("catalog/brands", () => fetchBrands())

  const { data: models, isLoading: modelsLoading } = useSWR(
    brand ? ["catalog/models", brand] : null,
    ([, b]) => fetchModels(b),
  )

  const { data: fuels, isLoading: fuelsLoading } = useSWR(
    brand ? ["catalog/fuels", brand, model] : null,
    ([, b, m]) => fetchFuels(b, m),
  )

  // Auto-select the only available fuel, when applicable.
  React.useEffect(() => {
    if (fuels && fuels.length === 1) {
      setFuel(fuels[0])
    }
  }, [fuels])

  const singleFuel = !!fuels && fuels.length === 1

  // --- Polling refs ---
  const pollTimer = React.useRef<ReturnType<typeof setInterval> | null>(null)
  const elapsedTimer = React.useRef<ReturnType<typeof setInterval> | null>(null)
  const abortRef = React.useRef<AbortController | null>(null)
  const startRef = React.useRef<number>(0)

  const stopTimers = React.useCallback(() => {
    if (pollTimer.current) {
      clearInterval(pollTimer.current)
      pollTimer.current = null
    }
    if (elapsedTimer.current) {
      clearInterval(elapsedTimer.current)
      elapsedTimer.current = null
    }
    abortRef.current?.abort()
    abortRef.current = null
  }, [])

  React.useEffect(() => stopTimers, [stopTimers])

  // --- Handlers ---
  function handleBrandChange(value: string | null) {
    setBrand(value ?? "")
    setModel("")
    setFuel("")
  }

  function handleModelChange(value: string | null) {
    setModel(value ?? "")
    setFuel("")
  }

  const runSearch = React.useCallback(async () => {
    setStatus("loading")
    setErrorMessage("")
    setResult(undefined)
    setElapsedMs(0)
    setSubmittedQuery({
      brand,
      model,
      fuel,
      yearMin: years[0],
      yearMax: years[1],
    })

    const controller = new AbortController()
    abortRef.current = controller
    startRef.current = Date.now()

    elapsedTimer.current = setInterval(() => {
      setElapsedMs(Date.now() - startRef.current)
    }, 250)

    try {
      const job = await startSearch(
        {
          email: email.trim().toLowerCase(),
          brand,
          model,
          fuel,
          year_min: years[0],
          year_max: years[1],
        },
        controller.signal,
      )

      // Recherche acceptée → un crédit vient d'être consommé côté serveur.
      setCredits((c) => (c != null && c > 0 ? c - 1 : c))

      pollTimer.current = setInterval(async () => {
        // Timeout guard.
        if (Date.now() - startRef.current > POLL_TIMEOUT_MS) {
          stopTimers()
          setErrorMessage("L'analyse a expiré, réessayez.")
          setStatus("error")
          return
        }

        try {
          const res = await fetchJob(job.job_id, controller.signal)
          if (res.status === "done") {
            stopTimers()
            setResult(res.result)
            setStatus("done")
            onAnalysisComplete?.(res.result)
          } else if (res.status === "error") {
            stopTimers()
            setErrorMessage(
              res.error || "L'analyse a échoué, réessayez.",
            )
            setStatus("error")
          }
        } catch (err) {
          if (err instanceof DOMException && err.name === "AbortError") return
          stopTimers()
          setErrorMessage("Service momentanément indisponible.")
          setStatus("error")
        }
      }, POLL_INTERVAL_MS)
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return
      stopTimers()
      if (err instanceof NeedCreditsError) {
        // Plus de crédit : on revient au formulaire, le bouton d'achat s'affiche.
        setCredits(0)
        setStatus("idle")
        return
      }
      setErrorMessage(
        err instanceof ApiError
          ? err.message
          : "Service momentanément indisponible.",
      )
      setStatus("error")
    }
  }, [email, brand, model, fuel, years, onAnalysisComplete, stopTimers])

  function handleCancel() {
    stopTimers()
    setStatus("idle")
    setElapsedMs(0)
  }

  function handleRetry() {
    setStatus("idle")
    setErrorMessage("")
  }

  const outOfCredits = emailValid && credits === 0
  const canSubmit =
    !!brand &&
    !!fuel &&
    emailValid &&
    credits != null &&
    credits > 0 &&
    status === "idle"

  const count =
    typeof result?.stats?.count === "number" ? result.stats.count : 0

  function handleReset() {
    setStatus("idle")
    setResult(undefined)
    setErrorMessage("")
    setElapsedMs(0)
  }

  if (status === "results" && result) {
    return (
      <ResultsDashboard
        result={result}
        query={submittedQuery}
        onNewSearch={handleReset}
      />
    )
  }

  return (
    <Card className="w-full rounded-2xl shadow-sm">
      <CardContent className="p-5 sm:p-6">
        <AnimatePresence mode="wait" initial={false}>
          {status === "idle" && (
            <motion.div
              key="idle"
              initial={{ opacity: 0, scale: 0.99 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.99 }}
              transition={transition}
            >
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  if (canSubmit) void runSearch()
                }}
              >
                <FieldGroup className="gap-5">
                  {/* Bandeau paiement réussi */}
                  {justPaid && (
                    <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-400">
                      ✓ 10 analyses ajoutées à votre compte.
                    </div>
                  )}

                  {/* Email */}
                  <Field>
                    <FieldLabel htmlFor="email">Email</FieldLabel>
                    <input
                      id="email"
                      type="email"
                      inputMode="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      onBlur={handleEmailBlur}
                      placeholder="vous@garage.fr"
                      className="h-9 w-full rounded-lg border border-input bg-transparent px-3 text-sm shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
                    />
                    {emailValid && credits != null && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        {credits > 0
                          ? `${credits} analyse${credits > 1 ? "s" : ""} restante${credits > 1 ? "s" : ""}`
                          : "Crédits épuisés"}
                      </p>
                    )}
                  </Field>

                  {/* Marque */}
                  <Field>
                    <FieldLabel htmlFor="brand">Marque</FieldLabel>
                    {brandsLoading ? (
                      <Skeleton className="h-9 w-full rounded-lg" />
                    ) : (
                      <Select
                        value={brand}
                        onValueChange={handleBrandChange}
                      >
                        <SelectTrigger
                          id="brand"
                          className="h-9 w-full"
                          disabled={!!brandsError}
                        >
                          <SelectValue placeholder="Choisissez une marque" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            {(brands ?? []).map((b) => (
                              <SelectItem key={b} value={b}>
                                {b}
                              </SelectItem>
                            ))}
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                    )}
                  </Field>

                  {/* Modèle */}
                  <Field>
                    <FieldLabel htmlFor="model">Modèle</FieldLabel>
                    {brand && modelsLoading ? (
                      <Skeleton className="h-9 w-full rounded-lg" />
                    ) : (
                      <Select
                        value={model}
                        onValueChange={handleModelChange}
                        disabled={!brand || (models ?? []).length === 0}
                      >
                        <SelectTrigger id="model" className="h-9 w-full">
                          <SelectValue placeholder="Tous les modèles" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            {(models ?? []).map((m) => (
                              <SelectItem key={m} value={m}>
                                {m}
                              </SelectItem>
                            ))}
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                    )}
                  </Field>

                  {/* Carburant */}
                  <Field>
                    <FieldLabel htmlFor="fuel">Carburant</FieldLabel>
                    {brand && fuelsLoading ? (
                      <Skeleton className="h-9 w-full rounded-lg" />
                    ) : (
                      <Select
                        value={fuel}
                        onValueChange={(v) => setFuel(v ?? "")}
                        disabled={
                          !brand ||
                          singleFuel ||
                          (fuels ?? []).length === 0
                        }
                      >
                        <SelectTrigger id="fuel" className="h-9 w-full">
                          <SelectValue placeholder="Choisissez un carburant">
                            {(value: string | null) =>
                              value
                                ? fuelLabel(value)
                                : "Choisissez un carburant"
                            }
                          </SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            {(fuels ?? []).map((f) => (
                              <SelectItem key={f} value={f}>
                                {fuelLabel(f)}
                              </SelectItem>
                            ))}
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                    )}
                  </Field>

                  {/* Année */}
                  <YearRangeSlider
                    min={2000}
                    max={currentYear}
                    value={years}
                    onChange={setYears}
                  />

                  {outOfCredits ? (
                    <div className="flex flex-col gap-2">
                      <p className="text-sm text-muted-foreground">
                        Vous avez utilisé vos analyses gratuites.
                      </p>
                      <Button
                        type="button"
                        onClick={handleBuy}
                        disabled={checkoutLoading}
                        className="mt-1 h-10 w-full"
                      >
                        {checkoutLoading
                          ? "Redirection…"
                          : "Acheter 10 analyses — 2 €"}
                      </Button>
                      {buyError && (
                        <p className="text-sm text-destructive">{buyError}</p>
                      )}
                    </div>
                  ) : (
                    <Button
                      type="submit"
                      className="mt-1 h-10 w-full"
                      disabled={!canSubmit}
                    >
                      Lancer l&apos;analyse
                      <ArrowRight data-icon="inline-end" />
                    </Button>
                  )}
                </FieldGroup>
              </form>
            </motion.div>
          )}

          {status === "loading" && (
            <motion.div
              key="loading"
              initial={{ opacity: 0, scale: 0.99 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.99 }}
              transition={transition}
            >
              <LoadingState elapsedMs={elapsedMs} onCancel={handleCancel} />
            </motion.div>
          )}

          {status === "error" && (
            <motion.div
              key="error"
              initial={{ opacity: 0, scale: 0.99 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.99 }}
              transition={transition}
            >
              <ErrorState message={errorMessage} onRetry={handleRetry} />
            </motion.div>
          )}

          {status === "done" && (
            <motion.div
              key="done"
              initial={{ opacity: 0, scale: 0.99 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.99 }}
              transition={transition}
            >
              <DoneState
                count={count}
                onViewResults={() => setStatus("results")}
                onNewSearch={handleReset}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  )
}
