import type { NextConfig } from "next";
import path from "path";
import { fileURLToPath } from "url";

const projectRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  // Prevent Next from picking up /Users/vivek/package-lock.json as the monorepo root
  outputFileTracingRoot: projectRoot,
  turbopack: {
    root: projectRoot,
  },
  // Page on 127.0.0.1 can load HMR/assets from localhost:3001 in dev
  allowedDevOrigins: ["127.0.0.1", "localhost"],
};

export default nextConfig;
