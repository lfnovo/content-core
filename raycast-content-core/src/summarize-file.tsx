import React, { useState } from "react";
import {
  Form,
  ActionPanel,
  Action,
  Detail,
  useNavigation,
  showToast,
  Toast,
  open,
} from "@raycast/api";
import { summarizeContent, checkUvxAvailable, validateFile, isSupportedFile } from "./utils/content-core";
import { ContentResult } from "./utils/types";

interface FormValues {
  filePath: string;
  context: string;
}

function SummarizeFileForm() {
  const [fileError, setFileError] = useState<string | undefined>();
  const { push } = useNavigation();

  // Predefined context options
  const contextOptions = [
    { value: "", title: "General Summary", description: "Standard summary of the content" },
    { value: "bullet points", title: "Bullet Points", description: "Key points in bullet format" },
    { value: "executive summary", title: "Executive Summary", description: "Brief overview for decision makers" },
    { value: "key takeaways", title: "Key Takeaways", description: "Main insights and conclusions" },
    { value: "research summary", title: "Research Summary", description: "Academic paper or research summary" },
    { value: "meeting notes", title: "Meeting Notes", description: "Extract action items and decisions" },
    { value: "technical summary", title: "Technical Summary", description: "Focus on technical details and specs" },
    { value: "explain to a child", title: "Simple Explanation", description: "Easy to understand summary" },
  ];

  async function handleSubmit(values: FormValues) {
    // Validate file
    if (!values.filePath.trim()) {
      setFileError("File path is required");
      return;
    }

    const validation = validateFile(values.filePath);
    if (!validation.valid) {
      setFileError(validation.error);
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

    setFileError(undefined);

    // Process the file
    const result = await summarizeContent({
      source: values.filePath,
      sourceType: "file",
      context: values.context || undefined,
    });

    // Navigate to results
    push(<ResultsView result={result} context={values.context} />);
  }

  function dropFileHandler(files: string[]) {
    if (files.length > 0) {
      const filePath = files[0];
      const validation = validateFile(filePath);
      
      if (!validation.valid) {
        setFileError(validation.error);
        return "";
      }

      if (!isSupportedFile(filePath)) {
        setFileError("File type not supported. See supported file types below.");
        return "";
      }

      setFileError(undefined);
      return filePath;
    }
    return "";
  }

  function getContextIcon(context: string): string {
    switch (context) {
      case "bullet points": return "•";
      case "executive summary": return "💼";
      case "key takeaways": return "🎯";
      case "research summary": return "🔬";
      case "meeting notes": return "📝";
      case "technical summary": return "⚙️";
      case "explain to a child": return "👶";
      default: return "📄";
    }
  }

  return (
    <Form
      actions={
        <ActionPanel>
          <Action.SubmitForm title="Generate Summary" onSubmit={handleSubmit} />
          <Action 
            title="Choose File" 
            onAction={async () => {
              await open("file:///");
            }}
            shortcut={{ modifiers: ["cmd"], key: "o" }}
          />
          <Action.OpenInBrowser
            title="Get OpenAI API Key"
            url="https://platform.openai.com/api-keys"
            shortcut={{ modifiers: ["cmd"], key: "k" }}
          />
        </ActionPanel>
      }
    >
      <Form.TextField
        id="filePath"
        title="File Path"
        placeholder="/path/to/your/document.pdf"
        error={fileError}
        onChange={() => setFileError(undefined)}
        onDrop={dropFileHandler}
        info="Enter the full path to your file, or drag and drop a file here"
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
        title="Supported File Types"
        text={`Documents: PDF, Word, PowerPoint, Excel, Text, Markdown, HTML, EPUB
Media: MP4, AVI, MOV, MP3, WAV, M4A (transcript summaries)
Images: JPG, PNG, TIFF (OCR then summarize)
Archives: ZIP, TAR, GZ (extract and summarize contents)

Content Core will extract content and generate an AI-powered summary based on your selected style.`}
      />
    </Form>
  );
}

function ResultsView({ result, context }: { result: ContentResult; context: string }) {
  const contextDisplay = context || "General Summary";
  const fileName = result.metadata?.source.split('/').pop() || '';
  const fileExtension = fileName.split('.').pop()?.toUpperCase() || '';
  
  const markdown = result.success
    ? `# ${contextDisplay}

**File:** ${fileName}  
**Type:** ${fileExtension}  
**Processing Time:** ${result.metadata?.extractionTime?.toFixed(1)}s  
**Summary Length:** ${result.metadata?.contentLength?.toLocaleString()} characters

---

${result.content}`
    : `# Summarization Failed

**File:** ${fileName}  
**Error:** ${result.error}

**Common Issues:**
- File might be corrupted or unreadable
- For media files, ensure you have an OpenAI API key configured
- Large files might timeout (try smaller files first)
- Some file formats might require additional dependencies

**Solutions:**
- Check file permissions and accessibility
- Configure required API keys in preferences
- Try with a smaller or different file format`;

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
          <Action.OpenWith
            title="Open Original File"
            path={result.metadata?.source || ""}
            shortcut={{ modifiers: ["cmd"], key: "o" }}
          />
          <Action.ShowInFinder
            title="Show in Finder"
            path={result.metadata?.source || ""}
            shortcut={{ modifiers: ["cmd"], key: "f" }}
          />
          {result.success && (
            <>
              <Action.CreateSnippet
                title="Save as Snippet"
                snippet={{
                  text: result.content,
                  name: `Summary: ${fileName}`,
                  keyword: `summary-${fileName.replace(/\.[^/.]+$/, "").toLowerCase()}`,
                }}
                shortcut={{ modifiers: ["cmd"], key: "s" }}
              />
              <Action.CreateQuicklink
                title="Create File Quicklink"
                quicklink={{
                  link: `file://${result.metadata?.source}`,
                  name: `Summary: ${fileName}`,
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
            <Detail.Metadata.Label title="File Name" text={fileName} />
            <Detail.Metadata.Label title="File Type" text={fileExtension} />
            <Detail.Metadata.Label title="Summary Style" text={contextDisplay} />
            <Detail.Metadata.Label title="Source Path" text={result.metadata?.source || ""} />
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
  return <SummarizeFileForm />;
}