import React, { useState } from "react";
import {
  Form,
  ActionPanel,
  Action,
  Detail,
  useNavigation,
  showToast,
  Toast,
} from "@raycast/api";
import { summarizeContent, checkUvxAvailable, isValidUrl } from "./utils/content-core";
import { ContentResult } from "./utils/types";

interface FormValues {
  url: string;
  context: string;
}

function SummarizeUrlForm() {
  const [urlError, setUrlError] = useState<string | undefined>();
  const { push } = useNavigation();

  // Predefined context options
  const contextOptions = [
    { value: "", title: "General Summary", description: "Standard summary of the content" },
    { value: "bullet points", title: "Bullet Points", description: "Key points in bullet format" },
    { value: "executive summary", title: "Executive Summary", description: "Brief overview for decision makers" },
    { value: "key takeaways", title: "Key Takeaways", description: "Main insights and conclusions" },
    { value: "explain to a child", title: "Simple Explanation", description: "Easy to understand summary" },
    { value: "academic summary", title: "Academic Summary", description: "Scholarly analysis and summary" },
    { value: "action items", title: "Action Items", description: "Actionable tasks and next steps" },
  ];

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
    const result = await summarizeContent({
      source: values.url,
      sourceType: "url",
      context: values.context || undefined,
    });

    // Navigate to results
    push(<ResultsView result={result} context={values.context} />);
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
          <Action.SubmitForm title="Generate Summary" onSubmit={handleSubmit} />
          <Action.OpenInBrowser
            title="Get OpenAI API Key"
            url="https://platform.openai.com/api-keys"
            shortcut={{ modifiers: ["cmd"], key: "o" }}
          />
          <Action.OpenInBrowser
            title="Get Firecrawl API Key"
            url="https://www.firecrawl.dev/"
            shortcut={{ modifiers: ["cmd"], key: "f" }}
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
        info="Enter any web page URL to summarize its content"
      />
      <Form.Dropdown id="context" title="Summary Style" defaultValue="">
        {contextOptions.map((option) => (
          <Form.Dropdown.Item 
            key={option.value}
            value={option.value} 
            title={option.title}
            icon={getContextIcon(option.value)}
          />
        ))}
      </Form.Dropdown>
      <Form.Description 
        text="Content Core will extract and summarize the webpage content using AI. Different summary styles will format the output for specific use cases."
      />
    </Form>
  );
}

function getContextIcon(context: string): string {
  switch (context) {
    case "bullet points": return "•";
    case "executive summary": return "💼";
    case "key takeaways": return "🎯";
    case "explain to a child": return "👶";
    case "academic summary": return "🎓";
    case "action items": return "✅";
    default: return "📝";
  }
}

function ResultsView({ result, context }: { result: ContentResult; context: string }) {
  const contextDisplay = context || "General Summary";
  const pageTitle = result.metadata?.title || result.metadata?.source?.split('/').pop() || 'Web Page';
  
  const markdown = result.success
    ? `# ${contextDisplay}

**Source:** ${result.metadata?.source}  
**Processing Time:** ${result.metadata?.extractionTime?.toFixed(1)}s  
**Summary Length:** ${result.metadata?.contentLength?.toLocaleString()} characters

---

${result.content}`
    : `# Summarization Failed

**Source:** ${result.metadata?.source}  
**Error:** ${result.error}

**Common Issues:**
- The webpage might be behind a paywall or login
- Content might be heavily JavaScript-dependent
- The URL might not be accessible
- API rate limits might have been exceeded

**Solutions:**
- Try with a Firecrawl API key for better web scraping
- Ensure you have an OpenAI API key for AI summarization
- Check if the URL is publicly accessible`;

  return (
    <Detail
      markdown={markdown}
      actions={
        <ActionPanel>
          <Action.CopyToClipboard
            title="Copy Summary"
            content={result.content}
            shortcut={{ modifiers: ["cmd"], key: "c" }}
          />
          <Action.Paste
            title="Paste Summary"
            content={result.content}
            shortcut={{ modifiers: ["cmd"], key: "v" }}
          />
          <Action.OpenInBrowser
            title="Open Original URL"
            url={result.metadata?.source || ""}
            shortcut={{ modifiers: ["cmd"], key: "o" }}
          />
          {result.success && (
            <>
              <Action.CreateSnippet
                title="Save as Snippet"
                snippet={{
                  text: result.content,
                  name: `Summary: ${pageTitle}`,
                  keyword: `summary-${pageTitle.toLowerCase().replace(/\s+/g, '-')}`,
                }}
                shortcut={{ modifiers: ["cmd"], key: "s" }}
              />
              <Action.CreateQuicklink
                title="Create Quicklink"
                quicklink={{
                  link: result.metadata?.source || "",
                  name: `Summary: ${pageTitle}`,
                }}
                shortcut={{ modifiers: ["cmd"], key: "q" }}
              />
            </>
          )}
        </ActionPanel>
      }
      metadata={
        result.success ? (
          <Detail.Metadata>
            <Detail.Metadata.Label title="Source URL" text={result.metadata?.source || ""} />
            <Detail.Metadata.Label title="Summary Style" text={contextDisplay} />
            <Detail.Metadata.Label 
              title="Processing Time" 
              text={`${result.metadata?.extractionTime?.toFixed(1)}s`} 
            />
            <Detail.Metadata.Label 
              title="Summary Length" 
              text={`${result.metadata?.contentLength?.toLocaleString()} characters`} 
            />
            <Detail.Metadata.Separator />
            <Detail.Metadata.Label title="Tip" text="Use Cmd+C to copy or Cmd+S to save as snippet" />
          </Detail.Metadata>
        ) : undefined
      }
    />
  );
}

export default function Command() {
  return <SummarizeUrlForm />;
}