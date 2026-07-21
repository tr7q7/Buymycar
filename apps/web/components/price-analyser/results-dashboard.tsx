"use client"

import * as React from "react"
import { motion } from "motion/react"
import { ArrowLeft, ArrowUpDown, ExternalLink, Gauge } from "lucide-react"

import { cn } from "@/lib/utils"
import {
  confidenceMeta,
  formatMileage,
  formatPrice,
} from "@/lib/format"
import type { Listing, ResultData } from "@/lib/api"
import { fuelLabel } from "@/lib/api"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"

import { ScoreBadge } from "./score-badge"
import { PriceMileageChart } from "./price-mileage-chart"

interface Query {
  brand: string
  model: string
  specification?: string
  fuel: string
  yearMin: number
  yearMax: number
}

interface ResultsDashboardProps {
  result: ResultData
  query?: Query
  onNewSearch: () => void
}

type SortKey = "price" | "score"
type SortDir = "asc" | "desc"

const transition = { duration: 0.2, ease: "easeOut" as const }

function scoreValue(l: Listing): number {
  return l.score == null ? -1 : l.score
}

export function ResultsDashboard({
  result,
  query,
  onNewSearch,
}: ResultsDashboardProps) {
  const { listings, filter, strategy, market_estimate } = result
  const [sortKey, setSortKey] = React.useState<SortKey>("score")
  const [sortDir, setSortDir] = React.useState<SortDir>("desc")

  const title = React.useMemo(() => {
    if (!query) return "Résultats de l'analyse"
    const parts = [query.brand, query.model, query.specification].filter(Boolean)
    const name = parts.join(" ")
    const years =
      query.yearMin === query.yearMax
        ? `${query.yearMin}`
        : `${query.yearMin}–${query.yearMax}`
    return [name, query.fuel ? fuelLabel(query.fuel) : "", years]
      .filter(Boolean)
      .join(" · ")
  }, [query])

  const topDeals = React.useMemo(
    () =>
      [...listings]
        .filter((l) => l.score != null)
        .sort((a, b) => scoreValue(b) - scoreValue(a))
        .slice(0, 5),
    [listings],
  )

  const sorted = React.useMemo(() => {
    const factor = sortDir === "asc" ? 1 : -1
    return [...listings].sort((a, b) => {
      const va = sortKey === "price" ? a.price : scoreValue(a)
      const vb = sortKey === "price" ? b.price : scoreValue(b)
      return (va - vb) * factor
    })
  }, [listings, sortKey, sortDir])

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"))
    } else {
      setSortKey(key)
      setSortDir("desc")
    }
  }

  // Clic sur un point du graphique → défilement vers l'annonce (et son lien) + surbrillance.
  const [highlightId, setHighlightId] = React.useState<string | null>(null)
  const highlightTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null)

  const handlePointClick = React.useCallback((listing: Listing) => {
    setHighlightId(listing.id)
    requestAnimationFrame(() => {
      const els = document.querySelectorAll<HTMLElement>(
        `[data-listing-id="${listing.id}"]`,
      )
      // Cible l'élément réellement visible (carte mobile OU ligne de tableau desktop).
      const target =
        Array.from(els).find((el) => el.offsetParent !== null) ?? els[0]
      target?.scrollIntoView({ behavior: "smooth", block: "center" })
    })
    if (highlightTimer.current) clearTimeout(highlightTimer.current)
    highlightTimer.current = setTimeout(() => setHighlightId(null), 2600)
  }, [])

  React.useEffect(
    () => () => {
      if (highlightTimer.current) clearTimeout(highlightTimer.current)
    },
    [],
  )

  const hasListings = listings.length > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={transition}
      className="flex w-full flex-col gap-5"
    >
      {/* 1) Context bar */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <Button onClick={onNewSearch} className="h-10">
            <ArrowLeft data-icon="inline-start" />
            Nouvelle analyse
          </Button>
          {strategy === "elargie" && (
            <span className="inline-flex w-fit items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
              Recherche élargie
            </span>
          )}
        </div>
        <div className="flex flex-col gap-0.5">
          <h1 className="text-balance text-xl font-semibold tracking-tight sm:text-2xl">
            {title}
          </h1>
          <p className="text-sm text-muted-foreground">
            {filter.retained} annonce{filter.retained > 1 ? "s" : ""} retenue
            {filter.retained > 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* 2) Market KPIs */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard
          label="Valeur marché estimée"
          value={formatPrice(market_estimate?.estimated)}
          emphasize
        />
        <KpiCard
          label="Intervalle normal"
          value={
            market_estimate
              ? `${formatPrice(market_estimate.low)} – ${formatPrice(
                  market_estimate.high,
                )}`
              : "—"
          }
        />
        <KpiCard
          label="Annonces retenues"
          value={String(filter.retained)}
        />
        <KpiCard
          label="Confiance"
          value={market_estimate?.confidence ?? "—"}
          dotClass={
            market_estimate
              ? confidenceMeta(market_estimate.confidence).dotClass
              : undefined
          }
        />
      </div>

      {!hasListings ? (
        <Card className="rounded-2xl shadow-sm">
          <CardContent className="py-10">
            <div className="flex flex-col items-center gap-2 text-center">
              <div className="flex size-12 items-center justify-center rounded-2xl bg-muted">
                <Gauge className="size-5 text-muted-foreground" />
              </div>
              <p className="text-sm font-medium">Aucune annonce comparable</p>
              <p className="text-sm text-muted-foreground">
                Élargissez les critères pour obtenir une estimation.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* 3) Price vs mileage chart */}
          <Card className="rounded-2xl shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">Prix vs Kilométrage</CardTitle>
              <CardDescription>
                Chaque point est une annonce · les meilleures affaires sont
                entourées
              </CardDescription>
            </CardHeader>
            <CardContent>
              <PriceMileageChart
                listings={listings}
                onPointClick={handlePointClick}
              />
            </CardContent>
          </Card>

          {/* 4) Top bonnes affaires */}
          {topDeals.length > 0 && (
            <Card className="rounded-2xl shadow-sm">
              <CardHeader>
                <CardTitle className="text-base">
                  Top bonnes affaires
                </CardTitle>
                <CardDescription>
                  Les annonces au meilleur rapport qualité-prix
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {topDeals.map((l) => (
                  <DealRow key={l.id} listing={l} />
                ))}
              </CardContent>
            </Card>
          )}

          {/* 5) Listings table / cards */}
          <Card className="rounded-2xl shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">
                Toutes les annonces
              </CardTitle>
              <CardDescription>
                {listings.length} résultat{listings.length > 1 ? "s" : ""}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Mobile: stacked cards */}
              <div className="flex flex-col gap-3 md:hidden">
                <div className="flex gap-2">
                  <SortButton
                    active={sortKey === "price"}
                    dir={sortDir}
                    onClick={() => toggleSort("price")}
                  >
                    Prix
                  </SortButton>
                  <SortButton
                    active={sortKey === "score"}
                    dir={sortDir}
                    onClick={() => toggleSort("score")}
                  >
                    Score
                  </SortButton>
                </div>
                {sorted.map((l) => (
                  <ListingCard
                    key={l.id}
                    listing={l}
                    highlighted={highlightId === l.id}
                  />
                ))}
              </div>

              {/* Desktop: real table */}
              <div className="hidden md:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead scope="col">Titre</TableHead>
                      <TableHead scope="col" className="text-right">
                        Année
                      </TableHead>
                      <TableHead scope="col" className="text-right">
                        Kilométrage
                      </TableHead>
                      <TableHead scope="col" className="text-right">
                        <SortHeader
                          active={sortKey === "price"}
                          dir={sortDir}
                          onClick={() => toggleSort("price")}
                        >
                          Prix
                        </SortHeader>
                      </TableHead>
                      <TableHead scope="col">
                        <SortHeader
                          active={sortKey === "score"}
                          dir={sortDir}
                          onClick={() => toggleSort("score")}
                        >
                          Score
                        </SortHeader>
                      </TableHead>
                      <TableHead scope="col" className="text-right">
                        Lien
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sorted.map((l) => (
                      <TableRow
                        key={l.id}
                        data-listing-id={l.id}
                        className={cn(
                          "transition-colors",
                          highlightId === l.id && "bg-primary/10",
                        )}
                      >
                        <TableCell className="max-w-[280px]">
                          <span className="line-clamp-1 font-medium">
                            {l.title || `${l.brand} ${l.model}`}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {l.location}
                          </span>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {l.year}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMileage(l.mileage)}
                        </TableCell>
                        <TableCell className="text-right font-medium tabular-nums">
                          {formatPrice(l.price)}
                        </TableCell>
                        <TableCell>
                          <ScoreBadge score={l.score} showValue />
                        </TableCell>
                        <TableCell className="text-right">
                          <ListingLink url={l.url} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          {/* Relance rapide en bas de page (email et crédits conservés). */}
          <Button
            onClick={onNewSearch}
            className="h-11 w-full sm:mx-auto sm:w-auto sm:px-8"
          >
            <ArrowLeft data-icon="inline-start" />
            Nouvelle analyse
          </Button>
        </>
      )}
    </motion.div>
  )
}

function KpiCard({
  label,
  value,
  emphasize,
  dotClass,
}: {
  label: string
  value: string
  emphasize?: boolean
  dotClass?: string
}) {
  return (
    <Card className="rounded-2xl shadow-sm">
      <CardContent className="flex flex-col gap-1 p-4">
        <span className="text-xs font-medium text-muted-foreground">
          {label}
        </span>
        <span
          className={cn(
            "flex items-center gap-2 font-semibold tabular-nums",
            emphasize ? "text-2xl" : "text-base",
          )}
        >
          {dotClass && (
            <span className={cn("size-2 shrink-0 rounded-full", dotClass)} />
          )}
          <span className="text-pretty">{value}</span>
        </span>
      </CardContent>
    </Card>
  )
}

function DealRow({ listing }: { listing: Listing }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-border p-3">
      <div className="flex min-w-0 flex-col gap-1">
        <span className="line-clamp-1 text-sm font-medium">
          {listing.title || `${listing.brand} ${listing.model}`}
        </span>
        <span className="text-xs text-muted-foreground">
          {listing.year} · {formatMileage(listing.mileage)} · {listing.location}
        </span>
        <ScoreBadge score={listing.score} showValue className="mt-0.5" />
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <span className="font-semibold tabular-nums">
          {formatPrice(listing.price)}
        </span>
        <ListingLink url={listing.url} label="Voir l'annonce" />
      </div>
    </div>
  )
}

function ListingCard({
  listing,
  highlighted,
}: {
  listing: Listing
  highlighted?: boolean
}) {
  return (
    <div
      data-listing-id={listing.id}
      className={cn(
        "flex flex-col gap-2 rounded-xl border border-border p-3 transition-colors",
        highlighted && "border-primary bg-primary/10",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <span className="line-clamp-2 text-sm font-medium">
          {listing.title || `${listing.brand} ${listing.model}`}
        </span>
        <span className="shrink-0 font-semibold tabular-nums">
          {formatPrice(listing.price)}
        </span>
      </div>
      <p className="text-xs text-muted-foreground">
        {listing.year} · {formatMileage(listing.mileage)} · {listing.location}
      </p>
      <div className="flex items-center justify-between gap-2">
        <ScoreBadge score={listing.score} showValue />
        <ListingLink url={listing.url} label="Voir l'annonce" />
      </div>
    </div>
  )
}

function ListingLink({ url, label }: { url: string; label?: string }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 rounded-md text-xs font-medium text-primary underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
    >
      {label ?? "Voir"}
      <ExternalLink className="size-3" aria-hidden="true" />
    </a>
  )
}

function SortHeader({
  active,
  dir,
  onClick,
  children,
}: {
  active: boolean
  dir: SortDir
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-sort={active ? (dir === "asc" ? "ascending" : "descending") : "none"}
      className={cn(
        "inline-flex items-center gap-1 rounded-md font-medium focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        active ? "text-foreground" : "text-muted-foreground",
      )}
    >
      {children}
      <ArrowUpDown className="size-3" aria-hidden="true" />
    </button>
  )
}

function SortButton({
  active,
  dir,
  onClick,
  children,
}: {
  active: boolean
  dir: SortDir
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <Button
      type="button"
      variant={active ? "secondary" : "outline"}
      size="sm"
      onClick={onClick}
      className="flex-1"
    >
      {children}
      {active ? (
        <span className="text-xs text-muted-foreground">
          {dir === "asc" ? "↑" : "↓"}
        </span>
      ) : (
        <ArrowUpDown data-icon="inline-end" />
      )}
    </Button>
  )
}
