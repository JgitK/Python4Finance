import type { NextConfig } from "next";

// The app is static. Python writes the JSON in public/data, and the
// browser does all the math. No server code is necessary.
const nextConfig: NextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
