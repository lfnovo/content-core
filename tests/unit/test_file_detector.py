"""Tests for FileDetector class."""
import pytest
from pathlib import Path
from content_core.content.identification import FileDetector


class TestFileDetectorPDF:
    """Test PDF file detection functionality."""
    
    @pytest.fixture
    def detector(self):
        """Create a FileDetector instance."""
        return FileDetector()
    
    @pytest.fixture
    def test_pdf_path(self):
        """Get path to test PDF file."""
        return Path(__file__).parent.parent / "input_content" / "file.pdf"
    
    @pytest.mark.asyncio
    async def test_detect_pdf_file(self, detector, test_pdf_path):
        """Test detection of a valid PDF file."""
        # Ensure test file exists
        assert test_pdf_path.exists(), f"Test PDF file not found at {test_pdf_path}"
        
        # Detect file type
        detected_type = await detector.detect(str(test_pdf_path))
        
        # Assert it's detected as PDF
        assert detected_type == "application/pdf", f"Expected 'application/pdf', got '{detected_type}'"
    
    @pytest.mark.asyncio
    async def test_pdf_detection_with_wrong_extension(self, detector, test_pdf_path, tmp_path):
        """Test PDF detection works regardless of file extension."""
        # Copy PDF with wrong extension
        wrong_ext_path = tmp_path / "test.txt"
        wrong_ext_path.write_bytes(test_pdf_path.read_bytes())
        
        # Detect file type
        detected_type = await detector.detect(str(wrong_ext_path))
        
        # Should still detect as PDF based on content, not extension
        assert detected_type == "application/pdf", f"Expected 'application/pdf', got '{detected_type}'"
    
    @pytest.mark.asyncio
    async def test_pdf_detection_performance(self, detector, test_pdf_path):
        """Test PDF detection is performant (reads minimal bytes)."""
        import time
        
        # Measure detection time
        start_time = time.time()
        detected_type = await detector.detect(str(test_pdf_path))
        end_time = time.time()
        
        # Should be detected as PDF
        assert detected_type == "application/pdf"
        
        # Should be fast (under 100ms for signature-based detection)
        detection_time = (end_time - start_time) * 1000  # Convert to ms
        assert detection_time < 100, f"PDF detection took {detection_time:.2f}ms, expected < 100ms"


def _ogg_page(codec_id: bytes) -> bytes:
    """Build a minimal Ogg page carrying a codec identification header.

    Enough for signature detection, which only inspects the leading bytes.
    """
    page_header = (
        b"OggS"           # capture pattern
        + b"\x00"         # stream structure version
        + b"\x02"         # header type: beginning of stream
        + b"\x00" * 8     # granule position
        + b"\x01\x00\x00\x00"  # bitstream serial number
        + b"\x00" * 4     # page sequence number
        + b"\x00" * 4     # checksum
        + b"\x01"         # page segments
        + b"\x1e"         # segment table
    )
    return page_header + codec_id + b"\x00" * 64


class TestFileDetectorOgg:
    """Ogg container detection: Opus, Vorbis and Theora share the same magic bytes."""

    @pytest.fixture
    def detector(self):
        return FileDetector()

    @pytest.mark.asyncio
    async def test_detect_opus_by_signature(self, detector, tmp_path):
        """An Ogg/Opus file is audio, detected from its codec header."""
        opus_path = tmp_path / "voice_note.opus"
        opus_path.write_bytes(_ogg_page(b"OpusHead"))

        assert await detector.detect(str(opus_path)) == "audio/ogg"

    @pytest.mark.asyncio
    async def test_detect_opus_by_extension(self, detector, tmp_path):
        """The .opus extension maps to audio/ogg even when sniffing finds nothing.

        Regression: .opus was missing from the extension mapping, so these files
        raised UnsupportedTypeException.
        """
        opus_path = tmp_path / "voice_note.opus"
        opus_path.write_bytes(b"\x00" * 64)

        assert await detector.detect(str(opus_path)) == "audio/ogg"

    @pytest.mark.asyncio
    async def test_detect_ogg_vorbis_still_audio(self, detector, tmp_path):
        """Existing Ogg/Vorbis behavior is unchanged."""
        ogg_path = tmp_path / "clip.ogg"
        ogg_path.write_bytes(_ogg_page(b"\x01vorbis"))

        assert await detector.detect(str(ogg_path)) == "audio/ogg"

    @pytest.mark.asyncio
    async def test_ogg_theora_routes_as_video(self, detector, tmp_path):
        """Ogg video must not be mistaken for audio just by its container."""
        ogv_path = tmp_path / "clip.ogv"
        ogv_path.write_bytes(_ogg_page(b"\x80theora"))

        assert await detector.detect(str(ogv_path)) == "video/ogg"

def _zip_with_mimetype(path, mimetype, members):
    """Write a ZIP whose first member is an uncompressed `mimetype`, as ODF/EPUB do."""
    import zipfile

    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", mimetype, compress_type=zipfile.ZIP_STORED)
        for name in members:
            zf.writestr(name, '<?xml version="1.0"?>', compress_type=zipfile.ZIP_DEFLATED)


class TestFileDetectorOpenDocument:
    """ODF is identified by its `mimetype` ZIP member, not by extension."""

    ODF_MIMES = [
        "application/vnd.oasis.opendocument.text",
        "application/vnd.oasis.opendocument.spreadsheet",
        "application/vnd.oasis.opendocument.presentation",
    ]

    @pytest.fixture
    def detector(self):
        return FileDetector()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mime", ODF_MIMES)
    @pytest.mark.parametrize("name", ["document", "document.zip", "document.docx"])
    async def test_odf_detected_by_mimetype_member(self, detector, tmp_path, mime, name):
        """Missing or wrong extensions don't matter: the `mimetype` member decides."""
        path = tmp_path / name
        _zip_with_mimetype(path, mime, ["content.xml", "META-INF/manifest.xml"])

        assert await detector.detect(str(path)) == mime

    @pytest.mark.parametrize(
        "ext, mime",
        [(".odt", ODF_MIMES[0]), (".ods", ODF_MIMES[1]), (".odp", ODF_MIMES[2])],
    )
    def test_odf_extension_fallback(self, detector, ext, mime):
        assert detector._detect_by_extension(Path(f"file{ext}")) == mime

    @pytest.mark.asyncio
    async def test_epub_with_mimetype_member_unchanged(self, detector, tmp_path):
        path = tmp_path / "book.epub"
        _zip_with_mimetype(path, "application/epub+zip", ["META-INF/container.xml"])

        assert await detector.detect(str(path)) == "application/epub+zip"

    @pytest.mark.asyncio
    async def test_docx_without_mimetype_member_unchanged(self, detector, tmp_path):
        import zipfile

        path = tmp_path / "report.docx"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("[Content_Types].xml", '<?xml version="1.0"?>')
            zf.writestr("word/document.xml", '<?xml version="1.0"?>')

        assert (
            await detector.detect(str(path))
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    @pytest.mark.asyncio
    async def test_real_fixtures(self, detector):
        fixtures = Path(__file__).parent.parent / "input_content"
        assert await detector.detect(str(fixtures / "file.odt")) == self.ODF_MIMES[0]
        assert await detector.detect(str(fixtures / "file.ods")) == self.ODF_MIMES[1]
        assert await detector.detect(str(fixtures / "file.odp")) == self.ODF_MIMES[2]
        assert await detector.detect(str(fixtures / "file.epub")) == "application/epub+zip"


@pytest.mark.asyncio
async def test_oversized_mimetype_member_read_is_bounded(tmp_path, monkeypatch):
    """A huge `mimetype` member is not decompressed in full just to sniff it."""
    import zipfile

    path = tmp_path / "bomb.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "mimetype",
            "application/vnd.oasis.opendocument.text" + " " * 5_000_000,
            compress_type=zipfile.ZIP_DEFLATED,
        )

    reads = []
    real_open = zipfile.ZipFile.open

    def tracking_open(self, name, *args, **kwargs):
        member = real_open(self, name, *args, **kwargs)
        real_read = member.read

        def read(n=-1):
            data = real_read(n)
            reads.append(len(data))
            return data

        member.read = read
        return member

    monkeypatch.setattr(zipfile.ZipFile, "open", tracking_open)

    detected = await FileDetector().detect(str(path))

    assert detected == "application/vnd.oasis.opendocument.text"
    assert reads and max(reads) <= FileDetector.ZIP_MIMETYPE_READ_SIZE
