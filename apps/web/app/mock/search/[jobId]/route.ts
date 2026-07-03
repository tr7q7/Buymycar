let calls = 0

export async function GET() {
  calls++
  // Resolve to "done" after a couple of polls to demo the loading state.
  if (calls < 3) {
    return Response.json({ job_id: "mock-job-123", status: "running" })
  }
  calls = 0
  return Response.json({
    job_id: "mock-job-123",
    status: "done",
    result: { stats: { count: 142 } },
  })
}
