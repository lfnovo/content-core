/// <reference types="@raycast/api">

/* 🚧 🚧 🚧
 * This file is auto-generated from the extension's manifest.
 * Do not modify manually. Instead, update the `package.json` file.
 * 🚧 🚧 🚧 */

/* eslint-disable @typescript-eslint/ban-types */

type ExtensionPreferences = {
  /** OpenAI API Key - Required for audio/video transcription and AI-powered content cleaning */
  "openaiApiKey"?: string,
  /** Firecrawl API Key - Optional: For enhanced web crawling and content extraction */
  "firecrawlApiKey"?: string,
  /** Jina API Key - Optional: Alternative web crawling service (fallback) */
  "jinaApiKey"?: string
}

/** Preferences accessible in all the extension's commands */
declare type Preferences = ExtensionPreferences

declare namespace Preferences {
  /** Preferences accessible in the `extract-content` command */
  export type ExtractContent = ExtensionPreferences & {}
  /** Preferences accessible in the `summarize-content` command */
  export type SummarizeContent = ExtensionPreferences & {}
  /** Preferences accessible in the `quick-extract` command */
  export type QuickExtract = ExtensionPreferences & {}
}

declare namespace Arguments {
  /** Arguments passed to the `extract-content` command */
  export type ExtractContent = {}
  /** Arguments passed to the `summarize-content` command */
  export type SummarizeContent = {}
  /** Arguments passed to the `quick-extract` command */
  export type QuickExtract = {
  /** URL or file path to extract */
  "source": string
}
}

