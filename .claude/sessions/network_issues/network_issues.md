# Problemas de Rede e Tratamento de Erros - YouTube Processor

## Problema Identificado

O processador de YouTube no `content-core` está falhando silenciosamente em ambiente de produção (Azure), retornando conteúdo vazio em vez de erros específicos. Isso impede que as aplicações cliente (Streamlit) tratem adequadamente diferentes tipos de falha.

## Análise Técnica

### Logs Observados em Staging:
```
| ERROR | Failed to get video title: 'NoneType' object is not subscriptable  
| ERROR | content_core retornou objeto vazio - title: None, content: 0 chars
```

### Função Afetada: `get_video_title()` 
**Arquivo:** `src/content_core/processors/youtube.py:28`

```python
title = soup.find("meta", property="og:title")["content"]  # ← FALHA AQUI
```

**Problema:** Se `soup.find()` não encontra o elemento meta, retorna `None`. Acessar `None["content"]` gera `TypeError: 'NoneType' object is not subscriptable`.

### Função Afetada: `extract_transcript_pytubefix()`
**Arquivo:** `src/content_core/processors/youtube.py:139`

```python
yt = YouTube(url)  # ← Pode falhar por bloqueio/rate limiting
```

**Problema:** Falhas de rede, bloqueios, ou rate limiting retornam `(None, None)` sem distinção do tipo de erro.

## Cenários de Falha Identificados

1. **🚫 Bloqueio de Rede (Azure)**
   - YouTube pode estar bloqueando requests do Azure
   - IPs do Azure Container Apps podem estar em blocklist
   
2. **⏱️ Rate Limiting**
   - Muitas tentativas simultâneas de extração
   - Throttling por parte do YouTube
   
3. **🔗 Problemas de HTML Parsing**
   - YouTube pode estar servindo HTML diferente para bots
   - Meta tags `og:title` podem estar ausentes ou em formato diferente
   
4. **📹 Vídeo sem Legenda**
   - Vídeo existe mas não tem transcrições disponíveis
   - Cenário válido que deveria retornar mensagem específica

## Recomendações de Melhoria

### 1. Melhoria no `get_video_title()`

```python
async def get_video_title(video_id):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Adicionar headers para parecer um browser real
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url) as response:
                if response.status == 429:
                    raise YouTubeRateLimitError(f"Rate limited for video {video_id}")
                elif response.status == 403:
                    raise YouTubeBlockedError(f"Access blocked for video {video_id}")
                elif response.status != 200:
                    raise YouTubeNetworkError(f"HTTP {response.status} for video {video_id}")
                
                html = await response.text()

        soup = BeautifulSoup(html, "html.parser")
        
        # Tratamento robusto para diferentes formatos de meta tag
        title_element = (
            soup.find("meta", property="og:title") or 
            soup.find("meta", attrs={"name": "title"}) or
            soup.find("title")
        )
        
        if not title_element:
            raise YouTubeParsingError(f"No title found for video {video_id}")
        
        # Acessar content de forma segura
        if hasattr(title_element, 'get'):
            title = title_element.get("content") or title_element.get_text()
        else:
            title = title_element.get_text() if title_element else None
            
        if not title:
            raise YouTubeParsingError(f"Empty title for video {video_id}")
            
        return title.strip()

    except aiohttp.ClientTimeout:
        raise YouTubeTimeoutError(f"Timeout getting title for video {video_id}")
    except aiohttp.ClientError as e:
        raise YouTubeNetworkError(f"Network error getting title for video {video_id}: {e}")
    except YouTubeError:
        raise  # Re-raise custom YouTube errors
    except Exception as e:
        logger.error(f"Unexpected error getting video title for {video_id}: {e}")
        raise YouTubeUnknownError(f"Unexpected error for video {video_id}: {e}")
```

### 2. Melhoria no `extract_transcript_pytubefix()`

```python
def extract_transcript_pytubefix(url, languages=["en", "es", "pt"]):
    try:
        from pytubefix import YouTube
        
        # Configurar timeout e headers
        yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)
        
        logger.debug(f"Video title: {yt.title}")
        logger.debug(f"Available captions: {list(yt.captions.keys()) if yt.captions else 'None'}")

        if not yt.captions:
            raise YouTubeNoCaptionsError(f"No captions available for video: {url}")

        caption = None
        # Try to get captions in preferred languages
        for lang in languages:
            if lang in yt.captions:
                caption = yt.captions[lang]
                break
            elif f"a.{lang}" in yt.captions:
                caption = yt.captions[f"a.{lang}"]
                break
        
        # If no preferred language, use first available
        if not caption and yt.captions:
            first_key = list(yt.captions.keys())[0]
            caption = yt.captions[first_key]
            logger.info(f"Using non-preferred caption language: {first_key}")

        if not caption:
            raise YouTubeNoCaptionsError(f"No suitable captions found for: {url}")

        try:
            txt_captions = caption.generate_txt_captions()
            srt_captions = caption.generate_srt_captions()
            
            if not txt_captions or not txt_captions.strip():
                raise YouTubeEmptyCaptionsError(f"Empty captions for video: {url}")
                
            return txt_captions, srt_captions
            
        except Exception as e:
            logger.error(f"Error generating captions: {e}")
            raise YouTubeCaptionGenerationError(f"Failed to generate captions: {e}")

    except ImportError:
        raise YouTubeLibraryError("pytubefix library not available")
    except YouTubeError:
        raise  # Re-raise custom YouTube errors
    except Exception as e:
        error_msg = str(e).lower()
        if "blocked" in error_msg or "forbidden" in error_msg:
            raise YouTubeBlockedError(f"YouTube blocked access: {e}")
        elif "timeout" in error_msg:
            raise YouTubeTimeoutError(f"Timeout accessing YouTube: {e}")
        elif "rate" in error_msg or "429" in error_msg:
            raise YouTubeRateLimitError(f"Rate limited by YouTube: {e}")
        else:
            logger.error(f"Unexpected error in pytubefix: {e}")
            raise YouTubeUnknownError(f"Unexpected YouTube error: {e}")
```

### 3. Definir Classes de Exception Específicas

```python
# Adicionar no início do arquivo youtube.py

class YouTubeError(Exception):
    """Base exception for YouTube-related errors"""
    pass

class YouTubeNetworkError(YouTubeError):
    """Network-related YouTube errors"""
    pass

class YouTubeBlockedError(YouTubeError):
    """YouTube blocked the request"""
    pass

class YouTubeRateLimitError(YouTubeError):
    """Rate limited by YouTube"""
    pass

class YouTubeTimeoutError(YouTubeError):
    """Timeout accessing YouTube"""
    pass

class YouTubeParsingError(YouTubeError):
    """Error parsing YouTube page"""
    pass

class YouTubeNoCaptionsError(YouTubeError):
    """Video has no captions available"""
    pass

class YouTubeEmptyCaptionsError(YouTubeError):
    """Captions are empty"""
    pass

class YouTubeCaptionGenerationError(YouTubeError):
    """Error generating caption text"""
    pass

class YouTubeLibraryError(YouTubeError):
    """pytubefix library error"""
    pass

class YouTubeUnknownError(YouTubeError):
    """Unknown YouTube error"""
    pass
```

### 4. Atualizar Função Principal `extract_youtube_transcript()`

```python
async def extract_youtube_transcript(state: ProcessSourceState):
    """Extract transcript from YouTube video with proper error handling"""
    
    assert state.url, "No URL provided"
    logger.info(f"Extracting transcript from URL: {state.url}")
    
    languages = CONFIG.get("youtube_transcripts", {}).get(
        "preferred_languages", ["en", "es", "pt"]
    )

    try:
        video_id = await _extract_youtube_id(state.url)
        if not video_id:
            raise YouTubeParsingError(f"Could not extract video ID from URL: {state.url}")

        # Try to get title
        try:
            title = await get_video_title(video_id)
        except YouTubeError as e:
            logger.warning(f"Could not get video title: {e}")
            title = f"YouTube Video {video_id}"  # Fallback title

        # Extract transcript using pytubefix
        try:
            formatted_content, transcript_raw = extract_transcript_pytubefix(state.url, languages)
            
            if not formatted_content:
                raise YouTubeEmptyCaptionsError("Transcript extraction returned empty content")
                
            logger.info(f"Successfully extracted {len(formatted_content)} characters from {state.url}")
            
            return {
                "content": formatted_content,
                "title": title,
                "metadata": {"video_id": video_id, "transcript": transcript_raw},
            }
            
        except YouTubeNoCaptionsError:
            # This is a valid scenario - video exists but no captions
            logger.info(f"Video {video_id} has no captions available")
            return {
                "content": "",
                "title": title,
                "metadata": {
                    "video_id": video_id, 
                    "error": "no_captions",
                    "message": "Este vídeo não possui legendas/transcrições disponíveis"
                },
            }
            
    except YouTubeBlockedError as e:
        logger.error(f"YouTube blocked access: {e}")
        raise  # Re-raise so client can handle specifically
        
    except YouTubeRateLimitError as e:
        logger.error(f"YouTube rate limit exceeded: {e}")
        raise  # Re-raise so client can handle specifically
        
    except YouTubeTimeoutError as e:
        logger.error(f"YouTube access timeout: {e}")
        raise  # Re-raise so client can handle specifically
        
    except YouTubeError as e:
        logger.error(f"YouTube error: {e}")
        raise  # Re-raise all YouTube errors for client handling
        
    except Exception as e:
        logger.error(f"Unexpected error extracting YouTube transcript: {e}")
        raise YouTubeUnknownError(f"Unexpected error: {e}")
```

## Benefícios das Melhorias

### 1. **Diagnóstico Preciso**
- Aplicações cliente podem distinguir entre diferentes tipos de erro
- Logs mais informativos para debugging
- Mensagens específicas para usuários finais

### 2. **Robustez**
- Headers de User-Agent para evitar detecção de bot
- Timeouts configurados adequadamente
- Fallbacks para diferentes formatos de HTML

### 3. **Experiência do Usuário**
- Mensagens claras: "Vídeo bloqueado", "Sem legendas", "Rate limit excedido"
- Evita confusão com mensagens genéricas
- Permite retry inteligente para erros temporários

## Implementação no Cliente (Streamlit)

Com essas melhorias, o Streamlit poderá tratar os erros adequadamente:

```python
try:
    result = await extract_content({"url": youtube_url})
except YouTubeBlockedError:
    st.error("🚫 YouTube bloqueou o acesso. Tente novamente mais tarde.")
except YouTubeRateLimitError:
    st.error("⏱️ Muitas tentativas. Aguarde alguns minutos.")
except YouTubeNoCaptionsError:
    st.warning("📹 Vídeo encontrado, mas não possui legendas/transcrições.")
except YouTubeTimeoutError:
    st.error("🌐 Timeout na conexão. Verifique sua internet.")
except YouTubeError as e:
    st.error(f"❌ Erro do YouTube: {str(e)}")
```

## Testes Recomendados

1. **Vídeo com legendas** - deve extrair corretamente
2. **Vídeo sem legendas** - deve retornar erro específico
3. **URL inválida** - deve retornar erro de parsing
4. **Rate limiting simulado** - deve retornar erro específico
5. **Timeout simulado** - deve retornar erro de timeout

## Conclusão

Essas melhorias resolverão os problemas silenciosos de extração do YouTube e fornecerão feedback adequado tanto para desenvolvedores quanto para usuários finais. A implementação é backward-compatible e melhora significativamente a experiência do usuário.