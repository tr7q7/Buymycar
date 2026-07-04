"use client"

import * as React from "react"

import { cn } from "@/lib/utils"
import { SearchHeader } from "./search-header"
import { SearchForm } from "./search-form"

export function PriceAnalyser() {
  const [isResults, setIsResults] = React.useState(false)

  return (
    <div
      className={cn(
        "flex w-full flex-col gap-8 transition-[max-width] duration-300",
        isResults ? "max-w-5xl" : "max-w-[480px]",
      )}
    >
      {!isResults && <SearchHeader />}
      <SearchForm onViewChange={setIsResults} />
    </div>
  )
}
