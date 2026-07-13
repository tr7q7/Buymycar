"use client"

import * as React from "react"
import posthog from "posthog-js"
import { PostHogProvider } from "posthog-js/react"

import { getVisitorId } from "@/lib/api"

// Clés lues uniquement depuis l'environnement (jamais committées).
const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY
const POSTHOG_HOST =
  process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://eu.i.posthog.com"

let initialized = false

function initPostHog() {
  if (initialized || typeof window === "undefined" || !POSTHOG_KEY) return
  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    // On n'envoie que nos événements métier : pas d'autocapture ni de pageview auto.
    autocapture: false,
    capture_pageview: false,
    person_profiles: "identified_only",
  })
  initialized = true
}

export function Providers({ children }: { children: React.ReactNode }) {
  React.useEffect(() => {
    if (!POSTHOG_KEY) return
    initPostHog()
    // Identité canonique = visitor_id → tous les événements (front + back) sont
    // reliés au même utilisateur.
    const visitorId = getVisitorId()
    if (visitorId) posthog.identify(visitorId)
    posthog.capture("landing_page_view")
  }, [])

  return <PostHogProvider client={posthog}>{children}</PostHogProvider>
}
