import React, { useState } from "react";
import {
  Form,
  ActionPanel,
  Action,
  Detail,
  useNavigation,
  showToast,
  Toast,
  Clipboard,
  getPreferenceValues,
} from "@raycast/api";
import { extractContent, checkUvxAvailable, isValidUrl } from "./utils/content-core";
import { ContentResult } from "./utils/types";

interface FormValues {
  url: string;
  format: string;
}

function ExtractUrlForm() {
  const [urlError, setUrlError] = useState<string | undefined>();
  const { push } = useNavigation();

  async function handleSubmit(values: FormValues) {
    // Validate URL
    if (!values.url.trim()) {
      setUrlError("URL is required");
      return;
    }

    if (!isValidUrl(values.url)) {
      setUrlError("Please enter a valid URL");
      return;
    }

    // Check if uvx is available
    if (!checkUvxAvailable()) {
      await showToast({
        style: Toast.Style.Failure,
        title: "uvx not found",
        message: "Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh",
      });
      return;
    }

    setUrlError(undefined);

    // Process the URL
    const result = await extractContent({
      source: values.url,
      sourceType: "url",
      format: values.format as "text" | "json" | "xml",
    });

    // Navigate to results
    push(<ResultsView result={result} />);
  }

  function dropUrlHandler(url: string) {
    if (isValidUrl(url)) {
      setUrlError(undefined);
      return url;
    }
    setUrlError("Dropped text is not a valid URL");
    return "";
  }

  return (
    <Form
      actions={
        <ActionPanel>
          <Action.SubmitForm title="Extract Content" onSubmit={handleSubmit} />
          <Action.OpenInBrowser
            title="Get Firecrawl API Key"
            url="https://www.firecrawl.dev/"
            shortcut={{ modifiers: ["cmd"], key: "f" }}
          />
          <Action.OpenInBrowser
            title="Get OpenAI API Key"
            url="https://platform.openai.com/api-keys"
            shortcut={{ modifiers: ["cmd"], key: "o" }}
          />
        </ActionPanel>
      }
    >
      <Form.TextField
        id="url"
        title="URL"
        placeholder="https://example.com/article"
        error={urlError}
        onChange={() => setUrlError(undefined)}
        onDrop={dropUrlHandler}
        info="Enter any web page URL to extract its content"
      />
      <Form.Dropdown id="format" title="Output Format" defaultValue="text">
        <Form.Dropdown.Item value="text" title="Plain Text" icon="📄" />
        <Form.Dropdown.Item value="json" title="JSON" icon="📋" />
        <Form.Dropdown.Item value="xml" title="XML" icon="📊" />
      </Form.Dropdown>
      <Form.Description text="Content Core will automatically select the best extraction method for the URL" />
    </Form>
  );
}

function ResultsView({ result }: { result: ContentResult }) {
  const markdown = result.success
    ? `# Content Extraction Results

**Source:** ${result.metadata?.source}  
**Extraction Time:** ${result.metadata?.extractionTime?.toFixed(1)}s  
**Content Length:** ${result.metadata?.contentLength?.toLocaleString()} characters

---

${result.content}`
    : `# Extraction Failed

**Source:** ${result.metadata?.source}  
**Error:** ${result.error}

Please check your URL and try again. Make sure you have the required API keys configured in preferences if processing complex content.`;

  return (
    <Detail
      markdown={markdown}
      actions={
        <ActionPanel>
          <Action.CopyToClipboard
            title="Copy Content"
            content={result.content}
            shortcut={{ modifiers: ["cmd"], key: "c" }}
          />
          <Action.Paste
            title="Paste Content"
            content={result.content}
            shortcut={{ modifiers: ["cmd"], key: "v" }}
          />
          <Action.CreateQuicklink
            title="Create Quicklink"
            quicklink={{
              link: result.metadata?.source || "",
              name: result.metadata?.title || "Extracted Content",
            }}
          />
          {result.success && (
            <Action.Push
              title="Summarize This Content"
              target={<SummarizeExtractedContent content={result.content} source={result.metadata?.source || ""} />}
              shortcut={{ modifiers: ["cmd"], key: "s" }}
            />
          )}
        </ActionPanel>
      }
      metadata={
        result.success ? (
          <Detail.Metadata>
            <Detail.Metadata.Label title="Source" text={result.metadata?.source || ""} />
            <Detail.Metadata.Label title="Type" text="URL" />
            <Detail.Metadata.Label 
              title="Extraction Time" 
              text={`${result.metadata?.extractionTime?.toFixed(1)}s`} 
            />
            <Detail.Metadata.Label 
              title="Content Length" 
              text={`${result.metadata?.contentLength?.toLocaleString()} characters`} 
            />
            <Detail.Metadata.Separator />
            <Detail.Metadata.Label title="Tip" text="Use Cmd+C to copy or Cmd+S to summarize" />
          </Detail.Metadata>
        ) : undefined
      }
    />
  );
}

function SummarizeExtractedContent({ content, source }: { content: string; source: string }) {
  const [context, setContext] = useState("");
  const { push } = useNavigation();

  async function handleSummarize() {
    // For already extracted content, we'll create a temp file approach
    // In a real implementation, you might want to use Content Core's direct text processing
    await showToast({
      style: Toast.Style.Animated,
      title: "Summarizing content...",
      message: "Processing extracted text",
    });

    // For now, we'll show a placeholder - in reality you'd implement direct text summarization
    push(
      <Detail 
        markdown={`# Summary Feature Coming Soon

This feature will allow you to summarize already extracted content with custom context.

**Original Source:** ${source}
**Content Length:** ${content.length.toLocaleString()} characters
**Requested Context:** ${context || "General summary"}

For now, please use the "Summarize URL" command directly on the original URL.`}
      />
    );
  }

  return (
    <Form
      actions={
        <ActionPanel>
          <Action title="Generate Summary" onAction={handleSummarize} />
        </ActionPanel>
      }
    >
      <Form.TextField
        id="context"
        title="Summary Context"
        placeholder="e.g., bullet points, executive summary, explain to a child"
        value={context}
        onChange={setContext}
        info="Optional: Provide context for how you want the content summarized"
      />
      <Form.TextArea
        id="preview"
        title="Content Preview"
        value={content.slice(0, 500) + (content.length > 500 ? "..." : "")}
        onChange={() => {}} // Read-only
      />
    </Form>
  );
}

export default function Command() {
  return <ExtractUrlForm />;
}