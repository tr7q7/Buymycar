/** @type {import('next').NextConfig} */
const nextConfig = {
  // Masque l'indicateur "Next.js Dev Tools" (coulisse technique) même en dev.
  devIndicators: false,
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
