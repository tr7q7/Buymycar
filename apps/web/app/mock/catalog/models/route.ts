export async function GET(req: Request) {
  await new Promise((r) => setTimeout(r, 400))
  const brand = new URL(req.url).searchParams.get("brand")
  const map: Record<string, string[]> = {
    Renault: ["Clio", "Megane", "Captur"],
    Peugeot: ["208", "308", "3008"],
    Volkswagen: ["Golf", "Polo", "Tiguan"],
    Tesla: ["Model 3", "Model Y"],
    BMW: ["Serie 1", "Serie 3", "X1"],
  }
  return Response.json(brand ? (map[brand] ?? []) : [])
}
