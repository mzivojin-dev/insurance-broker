import type { NextConfig } from "next";

// Two ways to run:
//   npm run dev     the page on :3000; /client_service/* is proxied to the agents (one origin, no CORS)
//   npm run export  static files in out/, served from the same domain as the API in prod
const exporting = process.env.npm_lifecycle_event === "export";   // works in cmd, PowerShell and bash
const agents = process.env.AGENTS_ORIGIN ?? "http://localhost:8080";   // the docker compose gateway

const config: NextConfig = exporting
  ? { output: "export" }
  : {
      async rewrites() {
        return [{ source: "/client_service/:path*", destination: `${agents}/client_service/:path*` }];
      },
    };

export default config;
