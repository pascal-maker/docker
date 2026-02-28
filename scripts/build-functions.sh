#!/usr/bin/env bash
# Build functions/shared and all TypeScript functions for GCP Cloud Functions deploy.
# Produces functions/<name>/.deploy/ with dist/, package.json, package-lock.json, shared/.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Building functions/shared ==="
cd functions/shared && pnpm build && cd ../..

echo "=== Building functions/github_webhook ==="
cd functions/github_webhook && pnpm build && cd ../..

echo "=== Building functions/auth_callback ==="
cd functions/auth_callback && pnpm build && cd ../..

echo "=== Building functions/auth_register_device ==="
cd functions/auth_register_device && pnpm build && cd ../..

deploy_function() {
  local name=$1
  local pkg_name=$2
  local deploy_dir=functions/${name}/.deploy

  cd "$(dirname "$0")/.." || exit 1

  echo "=== Preparing deploy package for ${name} ==="
  rm -rf "$deploy_dir"
  mkdir -p "$deploy_dir"

  cat > "$deploy_dir/package.json" << EOF
{
  "name": "${pkg_name}",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "dist/index.js",
  "engines": { "node": ">=20" },
  "dependencies": {
    "@google-cloud/functions-framework": "^5.0.0",
    "@refactor-agent/functions-shared": "file:./shared"
  }
}
EOF

  mkdir -p "$deploy_dir/shared"
  cp functions/shared/package.json "$deploy_dir/shared/"
  cp -r functions/shared/dist "$deploy_dir/shared/"
  cp -r functions/${name}/dist "$deploy_dir/"

  (cd "$deploy_dir" && npm install --package-lock-only)
}

deploy_function github_webhook github-webhook
deploy_function auth_callback auth-callback
deploy_function auth_register_device auth-register-device

echo "=== functions-build complete ==="
