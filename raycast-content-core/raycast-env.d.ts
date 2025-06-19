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
  /** Preferences accessible in the `extract-url` command */
  export type ExtractUrl = ExtensionPreferences & {}
  /** Preferences accessible in the `extract-file` command */
  export type ExtractFile = ExtensionPreferences & {}
  /** Preferences accessible in the `summarize-url` command */
  export type SummarizeUrl = ExtensionPreferences & {}
  /** Preferences accessible in the `summarize-file` command */
  export type SummarizeFile = ExtensionPreferences & {}
}

declare namespace Arguments {
  /** Arguments passed to the `extract-url` command */
  export type ExtractUrl = {}
  /** Arguments passed to the `extract-file` command */
  export type ExtractFile = {}
  /** Arguments passed to the `summarize-url` command */
  export type SummarizeUrl = {}
  /** Arguments passed to the `summarize-file` command */
  export type SummarizeFile = {}
}

