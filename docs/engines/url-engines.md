# URL Extraction Engines

Content Core supports multiple engines for extracting content from web URLs, with automatic fallback for reliability.

## Quick Comparison

| Engine | API Key | JavaScript | Speed | Best For |
|--------|---------|------------|-------|----------|
| **firecrawl** | Required | Yes | Fast | JS-heavy sites, best quality |
| **jina** | Optional | Limited | Fast | General use, good fallback |
| **crawl4ai** | No | Yes | Medium | Privacy-first, local |
| **bs4** (simple) | No | No | Fast | Simple HTML pages |

## Automatic Selection (Default)

With `url_engine: auto`, Content Core selects engines in this order:

1. **Firecrawl** - if `FIRECRAWL_API_KEY` is set
2. **Jina** - if available (optional API key for higher limits)
3. **Crawl4AI** - if installed
4. **BeautifulSoup** - always available

## Firecrawl

Best quality extraction with full JavaScript rendering.

### Setup

```bash
export FIRECRAWL_API_KEY=your-api-key
```

### Self-Hosted Option

Run your own Firecrawl instance:

```bash
# Set custom API URL
export FIRECRAWL_API_BASE_URL=http://localhost:3002
```

See [Firecrawl Self-Hosting Guide](https://github.com/mendableai/firecrawl/blob/main/SELF_HOST.md).

### Configuration

```yaml
extraction:
  url_engine: firecrawl
  firecrawl:
    api_url: null  # Custom URL for self-hosted
```

```python
from content_core.config import set_url_engine, set_firecrawl_api_url

set_url_engine("firecrawl")
set_firecrawl_api_url("http://localhost:3002")  # Optional
```

### Gotchas

- **No client-side proxy:** Configure proxy on server side
- **Rate limits:** Depends on your plan
- **Cost:** Per-request pricing on cloud version

---

## Jina

Good general-purpose extraction with optional API key.

### Setup

```bash
# Optional - increases rate limits
export JINA_API_KEY=your-api-key
```

### Configuration

```yaml
extraction:
  url_engine: jina
```

```python
from content_core.config import set_url_engine
set_url_engine("jina")
```

### Gotchas

- **Rate limits:** Without API key, aggressive rate limiting
- **JavaScript:** Limited JS rendering capability

---

## Crawl4AI

Local, privacy-first extraction using Playwright browser automation.

### Installation

```bash
pip install content-core[crawl4ai]

# Install Playwright browsers (required)
python -m playwright install --with-deps
```

### Configuration

```yaml
extraction:
  url_engine: crawl4ai
```

```python
from content_core.config import set_url_engine
set_url_engine("crawl4ai")
```

### When to Use

- Privacy-first: All processing local
- No API costs
- JavaScript-heavy sites
- Development and testing

### Gotchas

- **Browser dependencies:** Requires Playwright (~300MB)
- **Speed:** Slower than API-based engines
- **Resource usage:** Runs a browser instance

---

## BeautifulSoup (Simple)

Fast, lightweight extraction for simple HTML pages.

### Configuration

```yaml
extraction:
  url_engine: simple
```

```python
from content_core.config import set_url_engine
set_url_engine("simple")
```

### When to Use

- Simple static pages
- Speed is priority
- No JavaScript needed

### Gotchas

- **No JavaScript:** Cannot handle JS-rendered content
- **Basic extraction:** May miss dynamic content

---

## Per-Request Override

Override the engine for specific requests:

```python
import content_core as cc

# Use Firecrawl for this request
result = await cc.extract({
    "url": "https://example.com",
    "url_engine": "firecrawl"
})

# Use Crawl4AI for this request
result = await cc.extract({
    "url": "https://spa-app.com",
    "url_engine": "crawl4ai"
})
```

## Retry Configuration

All URL engines support automatic retry on transient failures:

```bash
# API-based engines (Firecrawl, Jina, Crawl4AI)
export CCORE_URL_API_MAX_RETRIES=3
export CCORE_URL_API_BASE_DELAY=1
export CCORE_URL_API_MAX_DELAY=30

# Network operations (HEAD requests, BeautifulSoup)
export CCORE_URL_NETWORK_MAX_RETRIES=3
export CCORE_URL_NETWORK_BASE_DELAY=0.5
export CCORE_URL_NETWORK_MAX_DELAY=10
```

## Proxy Configuration

Content Core supports proxy configuration through environment variables:

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1
```

**Note:** Firecrawl does NOT support client-side proxy. Configure proxy on the Firecrawl server.

## Comparison

| Feature | Firecrawl | Jina | Crawl4AI | BS4 |
|---------|-----------|------|----------|-----|
| JavaScript | Full | Limited | Full | None |
| API Key | Required | Optional | No | No |
| Self-hosted | Yes | No | N/A | N/A |
| Privacy | Cloud | Cloud | Local | Local |
| Speed | Fast | Fast | Medium | Fast |
| Quality | Excellent | Good | Good | Basic |
