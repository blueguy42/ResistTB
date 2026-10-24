import type { NextConfig } from "next";

// `pnpm build:static` (STATIC_EXPORT=1) writes plain HTML/JS/CSS to out/, with its own cache folder so it never
// disturbs a running `pnpm dev`. Set NEXT_PUBLIC_API_URL to the hosted API when you build it.
const staticExport = process.env.STATIC_EXPORT === "1";

const nextConfig: NextConfig = {
  /* config options here */
  // Cache Components and partial prefetching are server features (PPR) and cannot be used in export mode.
  ...(staticExport
    ? { output: "export" as const, distDir: ".next-export" }
    : { cacheComponents: true, partialPrefetching: true }),
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
