"use client"

import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"

interface YearRangeSliderProps {
  min: number
  max: number
  value: [number, number]
  onChange: (value: [number, number]) => void
  disabled?: boolean
}

export function YearRangeSlider({
  min,
  max,
  value,
  onChange,
  disabled,
}: YearRangeSliderProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">Année</Label>
        <div className="flex items-center gap-1.5 font-mono text-sm tabular-nums text-muted-foreground">
          <span className="rounded-md bg-muted px-1.5 py-0.5 text-foreground">
            {value[0]}
          </span>
          <span aria-hidden="true">–</span>
          <span className="rounded-md bg-muted px-1.5 py-0.5 text-foreground">
            {value[1]}
          </span>
        </div>
      </div>
      <Slider
        min={min}
        max={max}
        step={1}
        value={value}
        onValueChange={(v) => {
          const next = v as number[]
          onChange([next[0], next[1]])
        }}
        disabled={disabled}
        aria-label="Plage d'années"
        className="py-1.5"
      />
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  )
}
