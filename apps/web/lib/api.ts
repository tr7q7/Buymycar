// Typed fetch helpers for the LCB Price Analyser catalog + search API.
// The base URL is always read from the environment — never hardcoded.

const API = process.env.NEXT_PUBLIC_API_URL ?? ""

export type Fuel = "essence" | "diesel" | "electrique"

export type SearchStatus = "pending" | "running" | "done" | "error"

export interface SearchPayload {
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

function url(path: string): string {
  if (!API) {
    throw new ApiError("NEXT_PUBLIC_API_URL n'est pas configurée.")
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
  if (!res.ok) {
    throw new ApiError("Service momentanément indisponible.")
  }
  return (await res.json()) as SearchJob
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
