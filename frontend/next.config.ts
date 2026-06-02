import type { NextConfig } from "next";
import path from "path";
import { fileURLToPath } from "url";

const projectRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  // Self-contained server in .next/standalone for the Cloud Run Docker image.
  output: "standalone",
  // Pin the file-tracing/monorepo root to this app so Next doesn't walk up to a
  // parent lockfile.
  outputFileTracingRoot: projectRoot,
  turbopack: {
    root: projectRoot,
  },
  // Page on 127.0.0.1 can load HMR/assets from localhost:3001 in dev
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  // Enforce type checking on the production build. (ESLint runs via CI / `eslint .`;
  // Next 16 dropped the `eslint` config key.)
  typescript: { ignoreBuildErrors: false },
};

export default nextConfig;
