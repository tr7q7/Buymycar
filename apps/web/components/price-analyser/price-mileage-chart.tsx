"use client"

import * as React from "react"
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts"

import { formatMileage, formatNumber, formatPrice, scoreMeta } from "@/lib/format"
import type { Listing } from "@/lib/api"

const BEST_DEAL_THRESHOLD = 80

// Endpoints for the year gradient: muted (older) -> blue accent (newer).
const OLD_COLOR = [161, 161, 170] as const // neutral-400
const NEW_COLOR = [59, 130, 246] as const // blue-500

function lerpColor(t: number): string {
  const clamped = Math.max(0, Math.min(1, t))
  const r = Math.round(OLD_COLOR[0] + (NEW_COLOR[0] - OLD_COLOR[0]) * clamped)
  const g = Math.round(OLD_COLOR[1] + (NEW_COLOR[1] - OLD_COLOR[1]) * clamped)
  const b = Math.round(OLD_COLOR[2] + (NEW_COLOR[2] - OLD_COLOR[2]) * clamped)
  return `rgb(${r}, ${g}, ${b})`
}

interface Point {
  x: number
  y: number
  color: string
  isBest: boolean
  listing: Listing
}

interface PriceMileageChartProps {
  listings: Listing[]
  onPointClick?: (listing: Listing) => void
}

function DotShape(props: {
  cx?: number
  cy?: number
  payload?: Point
  onSelect?: (listing: Listing) => void
}) {
  const { cx, cy, payload, onSelect } = props
  if (cx == null || cy == null || !payload) return null
  const r = payload.isBest ? 7 : 4.5
  return (
    <g
      onClick={() => onSelect?.(payload.listing)}
      style={{ cursor: onSelect ? "pointer" : undefined }}
    >
      {payload.isBest && (
        <circle
          cx={cx}
          cy={cy}
          r={r + 3}
          fill="none"
          stroke="var(--primary)"
          strokeWidth={1.5}
          opacity={0.9}
        />
      )}
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill={payload.color}
        fillOpacity={payload.isBest ? 0.95 : 0.7}
        stroke="var(--background)"
        strokeWidth={1}
      />
    </g>
  )
}

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ payload: Point }>
}) {
  if (!active || !payload?.length) return null
  const point = payload[0]?.payload
  if (!point) return null
  const { listing } = point
  const meta = scoreMeta(listing.score)
  const label = listing.title || `${listing.brand} ${listing.model}`.trim()

  return (
    <div className="max-w-[220px] rounded-lg border border-border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="mb-1 line-clamp-2 font-medium text-popover-foreground">
        {label}
      </p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-muted-foreground">
        <dt>Année</dt>
        <dd className="text-right tabular-nums text-foreground">
          {listing.year}
        </dd>
        <dt>Kilométrage</dt>
        <dd className="text-right tabular-nums text-foreground">
          {formatMileage(listing.mileage)}
        </dd>
        <dt>Prix</dt>
        <dd className="text-right font-medium tabular-nums text-foreground">
          {formatPrice(listing.price)}
        </dd>
      </dl>
      <p className="mt-1.5 flex items-center gap-1.5 border-t border-border pt-1.5">
        <span className={`size-1.5 rounded-full ${meta.dotClass}`} />
        <span className={meta.textClass}>{meta.label}</span>
      </p>
    </div>
  )
}

export function PriceMileageChart({ listings, onPointClick }: PriceMileageChartProps) {
  const points = React.useMemo<Point[]>(() => {
    const years = listings.map((l) => l.year)
    const minYear = Math.min(...years)
    const maxYear = Math.max(...years)
    const span = maxYear - minYear || 1

    return listings.map((listing) => ({
      x: listing.mileage,
      y: listing.price,
      color: lerpColor((listing.year - minYear) / span),
      isBest: listing.score != null && listing.score >= BEST_DEAL_THRESHOLD,
      listing,
    }))
  }, [listings])

  return (
    <div className="h-[360px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 12, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--border)"
            vertical={false}
          />
          <XAxis
            type="number"
            dataKey="x"
            name="Kilométrage"
            tickFormatter={(v: number) => `${formatNumber(v / 1000)}k`}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            tickLine={false}
            axisLine={{ stroke: "var(--border)" }}
            padding={{ left: 12, right: 12 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Prix"
            tickFormatter={(v: number) => `${formatNumber(v / 1000)}k €`}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            tickLine={false}
            axisLine={{ stroke: "var(--border)" }}
            width={56}
          />
          <ZAxis range={[60, 60]} />
          <Tooltip
            cursor={{ strokeDasharray: "3 3", stroke: "var(--border)" }}
            content={<ChartTooltip />}
          />
          <Scatter
            data={points}
            shape={(props: object) => (
              <DotShape {...(props as { cx?: number; cy?: number; payload?: Point })} onSelect={onPointClick} />
            )}
            isAnimationActive={false}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
