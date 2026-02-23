/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GITHUB_OAUTH_CLIENT_ID?: string;
  readonly VITE_AUTH_CALLBACK_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
