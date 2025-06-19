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
import { extractContent, checkUvxAvailable, validateFile, getSupportedExtensions, isSupportedFile } from "./utils/content-core";
import { ContentResult } from "./utils/types";

interface FormValues {
  filePath: string;
  format: string;
}

function ExtractFileForm() {
  const [fileError, setFileError] = useState<string | undefined>();
  const { push } = useNavigation();

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
    const result = await extractContent({
      source: values.filePath,
      sourceType: "file",
      format: values.format as "text" | "json" | "xml",
    });

    // Navigate to results
    push(<ResultsView result={result} />);
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
        setFileError("File type not supported. See supported extensions below.");
        return "";
      }

      setFileError(undefined);
      return filePath;
    }
    return "";
  }

  return (
    <Form
      actions={
        <ActionPanel>
          <Action.SubmitForm title="Extract Content" onSubmit={handleSubmit} />
          <Action 
            title="Choose File" 
            onAction={async () => {
              await open("file:///");
            }}
            shortcut={{ modifiers: ["cmd"], key: "o" }}
          />
          <Action.OpenInBrowser
            title="Get OpenAI API Key (for media files)"
            url="https://platform.openai.com/api-keys"
            shortcut={{ modifiers: ["cmd"], key: "a" }}
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
      <Form.Dropdown id="format" title="Output Format" defaultValue="text">
        <Form.Dropdown.Item value="text" title="Plain Text" icon="📄" />
        <Form.Dropdown.Item value="json" title="JSON" icon="📋" />
        <Form.Dropdown.Item value="xml" title="XML" icon="📊" />
      </Form.Dropdown>
      <Form.Description 
        title="Supported File Types"
        text={`Documents: PDF, Word, PowerPoint, Excel, Text, Markdown, HTML, EPUB
Media: MP4, AVI, MOV, MP3, WAV, M4A (requires OpenAI API key)
Images: JPG, PNG, TIFF (OCR text extraction)
Archives: ZIP, TAR, GZ

Content Core will automatically detect the file type and use the best extraction method.`}
      />
    </Form>
  );
}

function ResultsView({ result }: { result: ContentResult }) {
  const fileName = result.metadata?.source.split('/').pop() || '';
  const fileExtension = fileName.split('.').pop()?.toUpperCase() || '';
  
  const markdown = result.success
    ? `# File Content Extraction Results

**File:** ${fileName}  
**Type:** ${fileExtension}  
**Extraction Time:** ${result.metadata?.extractionTime?.toFixed(1)}s  
**Content Length:** ${result.metadata?.contentLength?.toLocaleString()} characters

---

${result.content}`
    : `# Extraction Failed

**File:** ${fileName}  
**Error:** ${result.error}

**Troubleshooting:**
- Ensure the file exists and is readable
- For audio/video files, make sure you have an OpenAI API key configured
- For complex documents, check that all required dependencies are available
- Some files may require specific API keys for optimal extraction`;

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
            <Action.CreateSnippet
              title="Save as Snippet"
              snippet={{
                text: result.content,
                name: `Extracted: ${fileName}`,
                keyword: fileName.replace(/\.[^/.]+$/, "").toLowerCase(),
              }}
              shortcut={{ modifiers: ["cmd"], key: "s" }}
            />
          )}
        </ActionPanel>
      }
      metadata={
        result.success ? (
          <Detail.Metadata>
            <Detail.Metadata.Label title="File Name" text={fileName} />
            <Detail.Metadata.Label title="File Type" text={fileExtension} />
            <Detail.Metadata.Label title="Source Path" text={result.metadata?.source || ""} />
            <Detail.Metadata.Label 
              title="Extraction Time" 
              text={`${result.metadata?.extractionTime?.toFixed(1)}s`} 
            />
            <Detail.Metadata.Label 
              title="Content Length" 
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
  return <ExtractFileForm />;
}