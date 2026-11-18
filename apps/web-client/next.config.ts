import type { NextConfig } from "next";

// No third-party telemetry, not even from the build tool (project rule: children and LGPD).
process.env.NEXT_TELEMETRY_DISABLED = "1";

const nextConfig: NextConfig = {
  devIndicators: false,
  reactStrictMode: true,
};

export default nextConfig;
