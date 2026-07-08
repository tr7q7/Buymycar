// Typed fetch helpers for the AutoCote catalog + search + credits API.
// The base URL is always read from the environment — never hardcoded.

const API = process.env.NEXT_PUBLIC_API_URL ?? ""

export type Fuel = "essence" | "diesel" | "electrique"

export type SearchStatus = "pending" | "running" | "done" | "error"

export interface SearchPayload {
  email: string
  visitor_id: string
  brand: string
  model: string
  fuel: string
  year_min: number
  year_max: number
}

export interface SearchJob {
  job_id: string
  status: SearchStatus
}

export interface Credits {
  email: string
  credits_remaining: number
  device_blocked?: boolean
}

const VISITOR_STORAGE_KEY = "autocote_visitor_id"

/** Identifiant navigateur/appareil stable, persistant en localStorage. */
export function getVisitorId(): string {
  if (typeof window === "undefined") return ""
  let id = window.localStorage.getItem(VISITOR_STORAGE_KEY)
  if (!id) {
    id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`
    window.localStorage.setItem(VISITOR_STORAGE_KEY, id)
  }
  return id
}

export interface Listing {
  id: string
  brand: string
  model: string
  year: number
  mileage: number
  price: number
  fuel: string
  transmission: string
  location: string
  score: number | null
  title: string
  url: string
  image_url: string
}

export interface MarketEstimate {
  estimated: number
  low: number
  high: number
  confidence: string
  n_used: number
  effective_n: number
}

export interface ResultStats {
  count: number
  mean: number
  median: number
  min: number
  max: number
  stdev: number
}

export interface ResultFilter {
  level: number
  strict_count: number
  retained: number
  year_min_used: number
  year_max_used: number
}

export interface ResultData {
  listings: Listing[]
  stats: ResultStats
  filter: ResultFilter
  strategy: string
  market_estimate: MarketEstimate | null
}

export interface SearchJobResult {
  job_id: string
  status: SearchStatus
  result?: ResultData
  error?: string
}

/** Thrown when the API is unreachable or returns a non-OK response. */
export class ApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "ApiError"
  }
}

/** Thrown when a search is refused because the email has no credits left. */
export class NeedCreditsError extends Error {
  constructor() {
    super("NEED_CREDITS")
    this.name = "NeedCreditsError"
  }
}

function url(path: string): string {
  if (!API) {
    throw new ApiError("NEXT_PUBLIC_API_URL n'est pas configurée.")
  }
  // Garde-fou : en production, refuser les mocks de démonstration.
  // Évite d'afficher silencieusement de fausses données si l'env est mal réglée.
  if (process.env.NODE_ENV === "production" && API.startsWith("/mock")) {
    throw new ApiError(
      "Configuration invalide : NEXT_PUBLIC_API_URL pointe vers les mocks en production.",
    )
  }
  return `${API.replace(/\/$/, "")}${path}`
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  let res: Response
  try {
    res = await fetch(url(path), { signal })
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err
    throw new ApiError("Service momentanément indisponible.")
  }
  if (!res.ok) {
    throw new ApiError("Service momentanément indisponible.")
  }
  return (await res.json()) as T
}

export function fetchBrands(signal?: AbortSignal): Promise<string[]> {
  return getJson<string[]>("/catalog/brands", signal)
}

export function fetchModels(
  brand: string,
  signal?: AbortSignal,
): Promise<string[]> {
  return getJson<string[]>(
    `/catalog/models?brand=${encodeURIComponent(brand)}`,
    signal,
  )
}

export function fetchFuels(
  brand: string,
  model: string,
  signal?: AbortSignal,
): Promise<string[]> {
  const params = new URLSearchParams({ brand })
  if (model) params.set("model", model)
  return getJson<string[]>(`/catalog/fuels?${params.toString()}`, signal)
}

export async function startSearch(
  payload: SearchPayload,
  signal?: AbortSignal,
): Promise<SearchJob> {
  let res: Response
  try {
    res = await fetch(url("/search"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err
    throw new ApiError("Service momentanément indisponible.")
  }
  if (res.status === 402) {
    throw new NeedCreditsError()
  }
  if (!res.ok) {
    throw new ApiError("Service momentanément indisponible.")
  }
  return (await res.json()) as SearchJob
}

/** Crée l'email avec 2 crédits gratuits s'il est inconnu ; renvoie le solde.
 * visitor_id applique l'anti-abus par appareil (device_blocked dans la réponse). */
export async function initCredits(
  email: string,
  visitorId?: string,
  signal?: AbortSignal,
): Promise<Credits> {
  let res: Response
  try {
    res = await fetch(url("/credits/init"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, visitor_id: visitorId ?? "" }),
      signal,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err
    throw new ApiError("Service momentanément indisponible.")
  }
  if (!res.ok) {
    throw new ApiError("Service momentanément indisponible.")
  }
  return (await res.json()) as Credits
}

/** Consulte le solde de crédits d'un email. */
export function getCredits(email: string, signal?: AbortSignal): Promise<Credits> {
  return getJson<Credits>(
    `/credits?email=${encodeURIComponent(email)}`,
    signal,
  )
}

/** Crée une session Stripe Checkout (pack de 10 analyses) et renvoie l'URL. */
export async function createCheckoutSession(
  email: string,
  signal?: AbortSignal,
): Promise<{ url: string }> {
  let res: Response
  try {
    res = await fetch(url("/checkout/create-session"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
      signal,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err
    throw new ApiError("Service momentanément indisponible.")
  }
  if (!res.ok) {
    throw new ApiError("Paiement momentanément indisponible.")
  }
  return (await res.json()) as { url: string }
}

export function fetchJob(
  jobId: string,
  signal?: AbortSignal,
): Promise<SearchJobResult> {
  return getJson<SearchJobResult>(
    `/search/${encodeURIComponent(jobId)}`,
    signal,
  )
}

const FUEL_LABELS: Record<string, string> = {
  essence: "Essence",
  diesel: "Diesel",
  electrique: "Électrique",
}

export function fuelLabel(value: string): string {
  return FUEL_LABELS[value] ?? value
}
