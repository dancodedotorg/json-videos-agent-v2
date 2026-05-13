import type { NextConfig } from "next";

const agentUrl = process.env.AGENT_URL || "http://localhost:8080";

const nextConfig: NextConfig = {
  serverExternalPackages: ["@copilotkit/runtime"],
  typescript: {
    // HttpAgent type mismatch with CopilotRuntime — pending upstream fix
    ignoreBuildErrors: true,
  },
  async rewrites() {
    return [
      // Proxy preview data + SSE stream to ADK backend
      {
        source: "/preview/:path*",
        destination: `${agentUrl}/preview/:path*`,
      },
      // Proxy <json-video> web component assets to ADK backend
      {
        source: "/player/:path*",
        destination: `${agentUrl}/player/:path*`,
      },
    ];
  },
};

export default nextConfig;
