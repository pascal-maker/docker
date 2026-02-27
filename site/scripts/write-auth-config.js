#!/usr/bin/env node
/** Write auth/config.json with client_id for extension device flow. Run at build time. */
import { mkdirSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const clientId =
  process.env.VITE_GITHUB_APP_CLIENT_ID || process.env.VITE_GITHUB_OAUTH_CLIENT_ID || "";
const outDir = join(__dirname, "..", "public", "auth");
mkdirSync(outDir, { recursive: true });
writeFileSync(
  join(outDir, "config.json"),
  JSON.stringify({ clientId }, null, 0)
);
