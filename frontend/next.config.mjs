/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Produces a minimal self-contained server in .next/standalone for the Docker image.
  output: "standalone",
};

export default nextConfig;