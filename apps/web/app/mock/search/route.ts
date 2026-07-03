export async function POST() {
  return Response.json(
    { job_id: "mock-job-123", status: "pending" },
    { status: 202 },
  )
}
