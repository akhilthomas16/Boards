import type { NextConfig } from "next";

// Where the Next server reaches the API. Differs from NEXT_PUBLIC_API_URL inside Docker.
const apiUrl = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

const nextConfig: NextConfig = {
  turbopack: {},
  // Uploaded images are stored in markdown as /media/... — serve them from this origin.
  async rewrites() {
    return [{ source: "/media/:path*", destination: `${apiUrl}/media/:path*` }];
  },
};

export default nextConfig;
