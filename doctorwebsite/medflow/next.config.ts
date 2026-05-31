import type { NextConfig } from "next";
import path from "path";
import { fileURLToPath } from "url";

const projectRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  // Self-contained server in .next/standalone for the Cloud Run Docker image.
  output: "standalone",
  // Prevent Next from picking up /Users/vivek/package-lock.json as the monorepo root
  outputFileTracingRoot: projectRoot,
  turbopack: {
    root: projectRoot,
  },
  // Page on 127.0.0.1 can load HMR/assets from localhost:3001 in dev
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  // Don't fail the production image build on lint/type issues (hackathon deploy).
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
};

export default nextConfig;
