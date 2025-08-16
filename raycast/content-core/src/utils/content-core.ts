import { execFileSync, execSync } from "child_process";
import { existsSync } from "fs";
import { basename, extname } from "path";
import { getPreferenceValues, showToast, Toast } from "@raycast/api";
import { showFailureToast } from "@raycast/utils";
import { shellEnvSync } from "shell-env";
import { ContentResult, ProcessingOptions } from "./types";

// Get shell environment with proper PATH
const shellEnvironment = shellEnvSync();

/**
 * Get the path to uvx executable
 */
function getUvxPath(): string | null {
  const paths = [
    "/opt/homebrew/bin/uvx",
    "/usr/local/bin/uvx",
    "/Users/" + process.env.USER + "/.cargo/bin/uvx",
    "/Users/" + process.env.USER + "/.local/bin/uvx",
  ];

  // First try with shell environment PATH
  try {
    const result = execSync("which uvx", {
      encoding: "utf8",
      env: shellEnvironment,
    });
    return result.trim();
  } catch {
    // Try direct paths
    for (const path of paths) {
      try {
        execSync(path + " --version", { stdio: "ignore" });
        return path;
      } catch {
        continue;
      }
    }
  }
  return null;
}

/**
 * Check if uvx is available on the system
 */
export function checkUvxAvailable(): boolean {
  return getUvxPath() !== null;
}

/**
 * Setup environment variables from Raycast preferences
 */
function setupEnvironment(): Record<string, string> {
  const preferences = getPreferenceValues<Preferences>();
  const env: Record<string, string> = {
    ...shellEnvironment,
  };

  if (preferences.openaiApiKey) {
    env.OPENAI_API_KEY = preferences.openaiApiKey;
  }
  if (preferences.firecrawlApiKey) {
    env.FIRECRAWL_API_KEY = preferences.firecrawlApiKey;
  }
  if (preferences.jinaApiKey) {
    env.JINA_API_KEY = preferences.jinaApiKey;
  }

  return env;
}

/**
 * Validate URL format
 */
export function isValidUrl(string: string): boolean {
  try {
    new URL(string);
    return true;
  } catch {
    return false;
  }
}

/**
 * Validate file exists and is accessible
 */
export function validateFile(filePath: string): {
  valid: boolean;
  error?: string;
} {
  if (!filePath.trim()) {
    return { valid: false, error: "File path is required" };
  }

  if (!existsSync(filePath)) {
    return { valid: false, error: "File does not exist" };
  }

  return { valid: true };
}

/**
 * Extract content using Content Core
 */
export async function extractContent(
  options: ProcessingOptions,
): Promise<ContentResult> {
  const { source, sourceType, format = "text" } = options;

  // Validate input
  if (sourceType === "url" && !isValidUrl(source)) {
    return {
      success: false,
      content: "",
      error: "Invalid URL format",
    };
  }

  if (sourceType === "file") {
    const validation = validateFile(source);
    if (!validation.valid) {
      return {
        success: false,
        content: "",
        error: validation.error,
      };
    }
  }

  try {
    const env = setupEnvironment();
    const uvxPath = getUvxPath();

    if (!uvxPath) {
      throw new Error(
        "uvx not found. Please install uv first: brew install uv",
      );
    }

    // Build command arguments safely to prevent injection
    const args = ["--from", "content-core", "ccore", source];
    if (format !== "text") {
      args.push("--format", format);
    }

    await showToast({
      style: Toast.Style.Animated,
      title: "Extracting content...",
      message: `Processing ${sourceType}: ${basename(source) || source}`,
    });

    const startTime = Date.now();
    const output = execFileSync(uvxPath, args, {
      encoding: "utf8",
      env,
      timeout: 120000, // 2 minute timeout
    });

    const extractionTime = (Date.now() - startTime) / 1000;

    await showToast({
      style: Toast.Style.Success,
      title: "Content extracted successfully",
      message: `Processed in ${extractionTime.toFixed(1)}s`,
    });

    return {
      success: true,
      content: output.trim(),
      metadata: {
        source,
        sourceType,
        extractionTime,
        contentLength: output.length,
      },
    };
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error occurred";

    await showFailureToast(errorMessage, { title: "Extraction failed" });

    return {
      success: false,
      content: "",
      error: errorMessage,
      metadata: {
        source,
        sourceType,
      },
    };
  }
}

/**
 * Summarize content using Content Core
 */
export async function summarizeContent(
  options: ProcessingOptions,
): Promise<ContentResult> {
  const { source, sourceType, context } = options;

  // Validate input
  if (sourceType === "url" && !isValidUrl(source)) {
    return {
      success: false,
      content: "",
      error: "Invalid URL format",
    };
  }

  if (sourceType === "file") {
    const validation = validateFile(source);
    if (!validation.valid) {
      return {
        success: false,
        content: "",
        error: validation.error,
      };
    }
  }

  try {
    const env = setupEnvironment();
    const uvxPath = getUvxPath();

    if (!uvxPath) {
      throw new Error(
        "uvx not found. Please install uv first: brew install uv",
      );
    }

    // Build command arguments safely to prevent injection
    const args = ["--from", "content-core", "csum", source];
    if (context) {
      args.push("--context", context);
    }

    await showToast({
      style: Toast.Style.Animated,
      title: "Generating summary...",
      message: `Processing ${sourceType}: ${basename(source) || source}`,
    });

    const startTime = Date.now();
    const output = execFileSync(uvxPath, args, {
      encoding: "utf8",
      env,
      timeout: 120000, // 2 minute timeout
    });

    const extractionTime = (Date.now() - startTime) / 1000;

    await showToast({
      style: Toast.Style.Success,
      title: "Summary generated successfully",
      message: `Processed in ${extractionTime.toFixed(1)}s`,
    });

    return {
      success: true,
      content: output.trim(),
      metadata: {
        source,
        sourceType,
        extractionTime,
        contentLength: output.length,
      },
    };
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error occurred";

    await showFailureToast(errorMessage, { title: "Summarization failed" });

    return {
      success: false,
      content: "",
      error: errorMessage,
      metadata: {
        source,
        sourceType,
      },
    };
  }
}

/**
 * Get supported file extensions for Content Core
 */
export function getSupportedExtensions(): string[] {
  return [
    // Documents
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".txt",
    ".md",
    ".csv",
    ".html",
    ".epub",

    // Media
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".mp3",
    ".wav",
    ".m4a",
    ".flac",

    // Images
    ".jpg",
    ".jpeg",
    ".png",
    ".tiff",
    ".bmp",
    ".webp",

    // Archives
    ".zip",
    ".tar",
    ".gz",
  ];
}

/**
 * Check if file extension is supported
 */
export function isSupportedFile(filename: string): boolean {
  const ext = extname(filename).toLowerCase();
  return ext ? getSupportedExtensions().includes(ext) : false;
}
