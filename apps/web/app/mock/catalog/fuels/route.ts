export async function GET(req: Request) {
  await new Promise((r) => setTimeout(r, 400))
  const brand = new URL(req.url).searchParams.get("brand")
  // Tesla returns a single fuel to exercise the auto-select + disable path.
  if (brand === "Tesla") return Response.json(["electrique"])
  return Response.json(["essence", "diesel", "electrique"])
}
