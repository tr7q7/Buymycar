"use client"

import * as React from "react"

import { cn } from "@/lib/utils"
import { CreditsProvider } from "@/lib/credits-store"
import { SearchHeader } from "./search-header"
import { SearchForm } from "./search-form"
import { CreditCounter } from "./credit-counter"

export function PriceAnalyser() {
  const [isResults, setIsResults] = React.useState(false)

  return (
    <CreditsProvider>
      <div
        className={cn(
          "flex w-full flex-col gap-6 transition-[max-width] duration-300",
          isResults ? "max-w-5xl" : "max-w-[480px]",
        )}
      >
        {/* Compteur de crédits, toujours visible en haut de l'application. */}
        <CreditCounter />

        {!isResults && <SearchHeader />}
        <SearchForm onViewChange={setIsResults} />
      </div>
    </CreditsProvider>
  )
}
