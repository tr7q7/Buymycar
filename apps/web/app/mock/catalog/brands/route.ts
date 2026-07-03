export async function GET() {
  await new Promise((r) => setTimeout(r, 400))
  return Response.json(["Renault", "Peugeot", "Volkswagen", "Tesla", "BMW"])
}
