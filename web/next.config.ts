import type { NextConfig } from "next";
import { fileURLToPath } from "node:url";

// Static export: every page is rendered at build time into `out/`.
// No server, API routes or runtime data fetching are used (see README).
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  turbopack: {
    // Pin the project root to web/ so stray lockfiles in parent folders are ignored.
    root: fileURLToPath(new URL(".", import.meta.url)),
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
