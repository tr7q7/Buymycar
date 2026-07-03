import { SearchHeader } from "@/components/price-analyser/search-header"
import { SearchForm } from "@/components/price-analyser/search-form"

export default function Page() {
  return (
    <main className="flex min-h-screen items-start justify-center bg-background px-4 py-12 sm:items-center sm:py-16">
      <div className="flex w-full max-w-[480px] flex-col gap-8">
        <SearchHeader />
        <SearchForm />
      </div>
    </main>
  )
}
