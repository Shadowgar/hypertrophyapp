const serverApiBaseUrl =
  process.env.SERVER_API_BASE_URL || process.env.NEXT_SERVER_API_BASE_URL || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${serverApiBaseUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
