// Wrapper minimal autour de PostHog : un point d'entrée unique pour les
// événements métier (pas d'autocapture, on ne veut que ceux-ci).
import posthog from "posthog-js"

export function track(event: string, props?: Record<string, unknown>) {
  if (typeof window === "undefined") return
  posthog.capture(event, props)
}

// Relie l'email à l'identité canonique (visitor_id) sans changer le distinct_id.
export function identifyEmail(visitorId: string, email: string) {
  if (typeof window === "undefined" || !visitorId || !email) return
  posthog.identify(visitorId, { email })
}
