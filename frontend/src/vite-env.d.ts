/// <reference types="vite/client" />

// Build-time env vars exposed to the SPA. Only `VITE_`-prefixed vars are
// inlined by Vite, so we type them here for autocomplete + type-checking.
interface ImportMetaEnv {
  /**
   * Absolute URL the SPA uses as the API base, e.g. the Cloud Run service URL.
   * If unset, falls back to "/api" which works with Vite's dev proxy.
   */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
