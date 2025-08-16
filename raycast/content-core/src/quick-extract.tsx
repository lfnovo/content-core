import {
  LaunchProps,
  Clipboard,
  showToast,
  Toast,
  closeMainWindow,
} from "@raycast/api";
import { showFailureToast } from "@raycast/utils";
import { basename } from "path";
import {
  extractContent,
  checkUvxAvailable,
  isValidUrl,
  validateFile,
  isSupportedFile,
} from "./utils/content-core";

interface Arguments {
  source: string;
}

export default async function Command(
  props: LaunchProps<{ arguments: Arguments }>,
) {
  const { source } = props.arguments;

  try {
    // Validate input
    if (!source.trim()) {
      await showFailureToast(
        "Please provide a URL or file path to extract content from",
        {
          title: "Source Required",
        },
      );
      return;
    }

    // Auto-detect source type
    let sourceType: "url" | "file";
    if (isValidUrl(source)) {
      sourceType = "url";
    } else if (validateFile(source).valid && isSupportedFile(source)) {
      sourceType = "file";
    } else {
      await showFailureToast("Please provide a valid URL or file path", {
        title: "Invalid Source",
      });
      return;
    }

    // Additional validation
    if (sourceType === "file") {
      const validation = validateFile(source);
      if (!validation.valid) {
        await showFailureToast(validation.error || "File validation failed", {
          title: "File Error",
        });
        return;
      }

      if (!isSupportedFile(source)) {
        await showFailureToast("File type not supported by Content Core", {
          title: "Unsupported File Type",
        });
        return;
      }
    }

    // Check if uvx is available
    if (!checkUvxAvailable()) {
      await showFailureToast("Please install uv first: brew install uv", {
        title: "uvx not found",
      });
      return;
    }

    // Show processing toast
    const displayName = basename(source) || source;
    const typeDisplay = sourceType === "url" ? "URL" : "file";

    await showToast({
      style: Toast.Style.Animated,
      title: "Extracting content...",
      message: `Processing ${typeDisplay}: ${displayName}`,
    });

    // Close main window to get out of the way
    await closeMainWindow();

    // Extract content
    const result = await extractContent({
      source,
      sourceType,
      format: "text",
    });

    if (result.success) {
      // Copy to clipboard
      await Clipboard.copy(result.content);

      await showToast({
        style: Toast.Style.Success,
        title: "Content extracted!",
        message: `Copied ${result.metadata?.contentLength?.toLocaleString()} characters from ${typeDisplay} to clipboard`,
      });
    } else {
      await showFailureToast(result.error || "Unknown error occurred", {
        title: "Extraction failed",
      });
    }
  } catch (error) {
    await showFailureToast(
      error instanceof Error ? error.message : "Unknown error occurred",
      { title: "Error" },
    );
  }
}
