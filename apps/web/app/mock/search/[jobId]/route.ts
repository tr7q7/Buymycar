let calls = 0

const BRANDS_MODELS = ["Audi RS3"]
const FUELS = ["Essence"]
const TRANSMISSIONS = ["Automatique", "Manuelle"]
const LOCATIONS = [
  "Paris",
  "Lyon",
  "Marseille",
  "Bordeaux",
  "Lille",
  "Nantes",
  "Toulouse",
]

// Deterministic pseudo-random for stable demo data.
function rng(seed: number) {
  let s = seed
  return () => {
    s = (s * 9301 + 49297) % 233280
    return s / 233280
  }
}

function buildListings(count: number) {
  const rand = rng(42)
  const listings = Array.from({ length: count }, (_, i) => {
    const year = 2016 + Math.floor(rand() * 9) // 2016–2024
    const age = 2026 - year
    const mileage = Math.round((5000 + rand() * 22000) * age + rand() * 8000)
    // Price decreases with mileage/age, plus noise.
    const base = 78000 - age * 6500 - mileage * 0.18
    const price = Math.max(28000, Math.round((base + (rand() - 0.5) * 9000) / 100) * 100)
    // Score: cheaper-than-expected => higher score.
    const expected = 78000 - age * 6500 - mileage * 0.18
    const delta = (expected - price) / expected
    const score = Math.max(
      5,
      Math.min(98, Math.round(55 + delta * 220 + (rand() - 0.5) * 12)),
    )
    return {
      id: `lst-${i + 1}`,
      brand: "Audi",
      model: "RS3",
      year,
      mileage,
      price,
      fuel: FUELS[0],
      transmission: TRANSMISSIONS[i % TRANSMISSIONS.length],
      location: LOCATIONS[i % LOCATIONS.length],
      score: i % 11 === 0 ? null : score,
      title: `${BRANDS_MODELS[0]} ${year} ${TRANSMISSIONS[i % 2]}`,
      url: "https://www.lacentrale.fr",
      image_url: "",
    }
  })
  return listings
}

export async function GET() {
  calls++
  // Resolve to "done" after a couple of polls to demo the loading state.
  if (calls < 3) {
    return Response.json({ job_id: "mock-job-123", status: "running" })
  }
  calls = 0

  const listings = buildListings(38)
  const prices = listings.map((l) => l.price).sort((a, b) => a - b)
  const count = prices.length
  const mean = Math.round(prices.reduce((s, p) => s + p, 0) / count)
  const median = prices[Math.floor(count / 2)]
  const min = prices[0]
  const max = prices[count - 1]
  const stdev = Math.round(
    Math.sqrt(prices.reduce((s, p) => s + (p - mean) ** 2, 0) / count),
  )

  return Response.json({
    job_id: "mock-job-123",
    status: "done",
    result: {
      listings,
      stats: { count, mean, median, min, max, stdev },
      filter: {
        level: 0,
        strict_count: count,
        retained: count,
        year_min_used: 2018,
        year_max_used: 2026,
      },
      strategy: "stricte",
      market_estimate: {
        estimated: median,
        low: Math.round(median * 0.9),
        high: Math.round(median * 1.12),
        confidence: "Élevée",
        n_used: count,
        effective_n: count,
      },
    },
  })
}
