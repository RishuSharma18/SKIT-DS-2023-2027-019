/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly NEXT_PUBLIC_API_URL?: string;
  readonly NEXT_PUBLIC_WS_URL?: string;
  readonly NEXT_PUBLIC_AI_STREAM_URL?: string;
  readonly NEXT_PUBLIC_CAMERA_IDS?: string;
  readonly NEXT_PUBLIC_OVERSTAY_HOURS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
