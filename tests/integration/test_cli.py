import json
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest


@pytest.fixture
def fixture_path():
    """Provides the path to the directory containing test input files."""
    return Path(__file__).parent.parent / "input_content"


def run_cli_command(command_args, input_data=None):
    """Helper to run CLI commands and capture output."""
    try:
        result = subprocess.run(
            command_args,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result
    except subprocess.TimeoutExpired:
        pytest.fail(f"Command {command_args} timed out")


class TestCcoreCLI:
    """Tests for the ccore CLI command."""
    
    def test_ccore_help(self):
        """Test ccore help output."""
        result = run_cli_command([sys.executable, "-m", "content_core", "--help"])
        # Note: ccore is the default when running the module, but let's test the actual CLI entry points
        
    def test_ccore_text_input(self):
        """Test ccore with direct text input."""
        result = run_cli_command(["uv", "run", "ccore", "This is a test content."])
        
        assert result.returncode == 0
        assert "This is a test content." in result.stdout
        assert result.stderr == ""
    
    def test_ccore_file_input(self, fixture_path):
        """Test ccore with file input."""
        md_file = fixture_path / "file.md"
        if not md_file.exists():
            pytest.skip(f"Fixture file not found: {md_file}")
            
        result = run_cli_command(["uv", "run", "ccore", str(md_file)])
        
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0
        assert "Buenos Aires" in result.stdout
        
    def test_ccore_url_input(self):
        """Test ccore with URL input."""
        result = run_cli_command(["uv", "run", "ccore", "https://www.example.com"])
        
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0
        
    def test_ccore_json_format(self):
        """Test ccore with JSON output format."""
        result = run_cli_command(["uv", "run", "ccore", "-f", "json", "Test content for JSON output."])
        
        assert result.returncode == 0
        
        # Verify it's valid JSON
        output_data = json.loads(result.stdout)
        assert isinstance(output_data, dict)
        assert "content" in output_data
        assert "Test content for JSON output." in output_data["content"]
        
    def test_ccore_xml_format(self):
        """Test ccore with XML output format."""
        result = run_cli_command(["uv", "run", "ccore", "-f", "xml", "Test content for XML output."])
        
        assert result.returncode == 0
        
        # Verify it's valid XML
        root = ET.fromstring(result.stdout.strip())
        assert root.tag == "result"
        content_elem = root.find(".//content")
        assert content_elem is not None
        assert "Test content for XML output." in content_elem.text
        
    def test_ccore_text_format_explicit(self):
        """Test ccore with explicit text format."""
        result = run_cli_command(["uv", "run", "ccore", "-f", "text", "Test content for text output."])
        
        assert result.returncode == 0
        assert "Test content for text output." in result.stdout
        
    def test_ccore_stdin_input(self):
        """Test ccore with stdin input."""
        test_content = "This content comes from stdin."
        result = run_cli_command(["uv", "run", "ccore"], input_data=test_content)
        
        assert result.returncode == 0
        assert test_content in result.stdout
        
    def test_ccore_stdin_json_format(self):
        """Test ccore with stdin input and JSON format."""
        test_content = "Stdin content with JSON format."
        result = run_cli_command(["uv", "run", "ccore", "-f", "json"], input_data=test_content)
        
        assert result.returncode == 0
        
        # Verify it's valid JSON
        output_data = json.loads(result.stdout)
        assert test_content in output_data["content"]
        
    def test_ccore_debug_flag(self):
        """Test ccore with debug flag."""
        result = run_cli_command(["uv", "run", "ccore", "-d", "Debug test content."])
        
        assert result.returncode == 0
        assert "Debug test content." in result.stdout
        # Debug output goes to stderr in loguru
        
    def test_ccore_file_pdf(self, fixture_path):
        """Test ccore with PDF file."""
        pdf_file = fixture_path / "file.pdf"
        if not pdf_file.exists():
            pytest.skip(f"Fixture file not found: {pdf_file}")
            
        result = run_cli_command(["uv", "run", "ccore", str(pdf_file)])
        
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0


class TestCcleanCLI:
    """Tests for the cclean CLI command."""
    
    def test_cclean_text_input(self):
        """Test cclean with direct text input."""
        messy_text = "  This   is    messy    text   with   extra   spaces.  "
        result = run_cli_command(["uv", "run", "cclean", messy_text])
        
        assert result.returncode == 0
        cleaned = result.stdout.strip()
        assert cleaned != messy_text
        assert "This is messy text" in cleaned
        
    def test_cclean_json_input(self):
        """Test cclean with JSON input containing content field."""
        json_input = '{"content": "  Messy   JSON   content  "}'
        result = run_cli_command(["uv", "run", "cclean"], input_data=json_input)
        
        assert result.returncode == 0
        cleaned = result.stdout.strip()
        assert "Messy JSON content" in cleaned
        
    def test_cclean_xml_input(self):
        """Test cclean with XML input containing content field."""
        xml_input = '<root><content>  Messy   XML   content  </content></root>'
        result = run_cli_command(["uv", "run", "cclean"], input_data=xml_input)
        
        assert result.returncode == 0
        cleaned = result.stdout.strip()
        assert "Messy XML content" in cleaned
        
    def test_cclean_file_input(self, fixture_path):
        """Test cclean with file input."""
        txt_file = fixture_path / "file.txt"
        if not txt_file.exists():
            pytest.skip(f"Fixture file not found: {txt_file}")
            
        result = run_cli_command(["uv", "run", "cclean", str(txt_file)])
        
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0
        
    def test_cclean_url_input(self):
        """Test cclean with URL input."""
        result = run_cli_command(["uv", "run", "cclean", "https://www.example.com"])
        
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0
        
    def test_cclean_stdin_input(self):
        """Test cclean with stdin input."""
        messy_content = "  This    has   too   many    spaces   and needs   cleaning.  "
        result = run_cli_command(["uv", "run", "cclean"], input_data=messy_content)
        
        assert result.returncode == 0
        cleaned = result.stdout.strip()
        assert "This has too many spaces" in cleaned
        
    def test_cclean_debug_flag(self):
        """Test cclean with debug flag."""
        result = run_cli_command(["uv", "run", "cclean", "-d", "Debug clean test."])
        
        assert result.returncode == 0
        assert "Debug clean test" in result.stdout


class TestCsumCLI:
    """Tests for the csum CLI command."""
    
    def test_csum_text_input(self):
        """Test csum with direct text input."""
        long_text = "Artificial Intelligence is revolutionizing industries across the globe. From healthcare to finance, AI technologies are enabling automation, improving decision-making, and creating new possibilities for innovation."
        result = run_cli_command(["uv", "run", "csum", long_text])
        
        assert result.returncode == 0
        summary = result.stdout.strip()
        assert len(summary) > 0
        assert len(summary) < len(long_text)  # Summary should be shorter
        
    def test_csum_with_context(self):
        """Test csum with context parameter."""
        text = "Machine learning algorithms process vast amounts of data to identify patterns and make predictions."
        context = "explain in simple terms"
        result = run_cli_command(["uv", "run", "csum", "--context", context, text])
        
        assert result.returncode == 0
        summary = result.stdout.strip()
        assert len(summary) > 0
        
    def test_csum_file_input(self, fixture_path):
        """Test csum with file input."""
        md_file = fixture_path / "file.md"
        if not md_file.exists():
            pytest.skip(f"Fixture file not found: {md_file}")
            
        result = run_cli_command(["uv", "run", "csum", str(md_file)])
        
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0
        
    def test_csum_url_input(self):
        """Test csum with URL input."""
        result = run_cli_command(["uv", "run", "csum", "https://www.example.com"])
        
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0
        
    def test_csum_json_input(self):
        """Test csum with JSON input containing content field."""
        json_input = '{"content": "This is a long article about technology trends. It discusses various aspects of innovation, digital transformation, and the future of work in the digital age."}'
        result = run_cli_command(["uv", "run", "csum"], input_data=json_input)
        
        assert result.returncode == 0
        summary = result.stdout.strip()
        assert len(summary) > 0
        
    def test_csum_xml_input(self):
        """Test csum with XML input containing content field."""
        xml_input = '<article><content>This is a comprehensive guide to understanding cloud computing. It covers infrastructure, platforms, software services, and deployment models.</content></article>'
        result = run_cli_command(["uv", "run", "csum"], input_data=xml_input)
        
        assert result.returncode == 0
        summary = result.stdout.strip()
        assert len(summary) > 0
        
    def test_csum_stdin_input(self):
        """Test csum with stdin input."""
        long_content = "The Internet of Things (IoT) represents a network of interconnected devices that communicate and exchange data. This technology has applications in smart homes, industrial automation, healthcare monitoring, and environmental sensing. As IoT devices become more prevalent, they are transforming how we interact with our environment and creating new opportunities for data-driven insights."
        result = run_cli_command(["uv", "run", "csum"], input_data=long_content)
        
        assert result.returncode == 0
        summary = result.stdout.strip()
        assert len(summary) > 0
        assert len(summary) < len(long_content)
        
    def test_csum_context_bullet_points(self):
        """Test csum with bullet points context."""
        text = "Blockchain technology provides a decentralized approach to data storage and transaction processing. It ensures security through cryptographic methods and maintains transparency through distributed ledgers."
        result = run_cli_command(["uv", "run", "csum", "--context", "in bullet points", text])
        
        assert result.returncode == 0
        summary = result.stdout.strip()
        assert len(summary) > 0
        
    def test_csum_debug_flag(self):
        """Test csum with debug flag."""
        result = run_cli_command(["uv", "run", "csum", "-d", "Debug summary test content."])
        
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0


class TestCLIErrorHandling:
    """Tests for CLI error handling and edge cases."""
    
    def test_ccore_empty_input_error(self):
        """Test ccore with empty input should error."""
        result = run_cli_command(["uv", "run", "ccore", ""])
        
        assert result.returncode != 0
        
    def test_cclean_empty_input_error(self):
        """Test cclean with empty input should error."""
        result = run_cli_command(["uv", "run", "cclean", ""])
        
        assert result.returncode != 0
        
    def test_csum_empty_input_error(self):
        """Test csum with empty input should error."""
        result = run_cli_command(["uv", "run", "csum", ""])
        
        assert result.returncode != 0
        
    def test_ccore_invalid_format(self):
        """Test ccore with invalid format option."""
        result = run_cli_command(["uv", "run", "ccore", "-f", "invalid", "test"])
        
        assert result.returncode != 0
        assert "invalid choice" in result.stderr.lower()
        
    def test_ccore_nonexistent_file(self):
        """Test ccore with non-existent file."""
        result = run_cli_command(["uv", "run", "ccore", "/path/to/nonexistent/file.txt"])
        
        # Should not error but treat as text content
        assert result.returncode == 0
        assert "/path/to/nonexistent/file.txt" in result.stdout
        
    def test_stdin_no_content_error(self):
        """Test CLI with no content and no stdin should error."""
        # This is tricky to test as it involves TTY detection
        # We'll skip this for now as it requires special handling
        pass


class TestCLIIntegration:
    """Integration tests combining multiple CLI features."""
    
    def test_pipeline_extract_clean_summarize(self, fixture_path):
        """Test a pipeline of extract -> clean -> summarize."""
        md_file = fixture_path / "file.md"
        if not md_file.exists():
            pytest.skip(f"Fixture file not found: {md_file}")
            
        # Extract content
        extract_result = run_cli_command(["uv", "run", "ccore", str(md_file)])
        assert extract_result.returncode == 0
        
        # Clean extracted content
        clean_result = run_cli_command(["uv", "run", "cclean"], input_data=extract_result.stdout)
        assert clean_result.returncode == 0
        
        # Summarize cleaned content
        summary_result = run_cli_command(["uv", "run", "csum"], input_data=clean_result.stdout)
        assert summary_result.returncode == 0
        
        assert len(summary_result.stdout.strip()) > 0
        
    def test_json_pipeline(self):
        """Test pipeline with JSON format."""
        text = "This is a test for JSON pipeline processing."
        
        # Extract as JSON
        extract_result = run_cli_command(["uv", "run", "ccore", "-f", "json", text])
        assert extract_result.returncode == 0
        
        # Verify JSON output
        json_data = json.loads(extract_result.stdout)
        assert text in json_data["content"]
        
        # Clean JSON content
        clean_result = run_cli_command(["uv", "run", "cclean"], input_data=extract_result.stdout)
        assert clean_result.returncode == 0
        
        # Summarize cleaned content
        summary_result = run_cli_command(["uv", "run", "csum"], input_data=clean_result.stdout)
        assert summary_result.returncode == 0
        
    def test_xml_processing(self):
        """Test XML format processing."""
        text = "This is test content for XML processing and validation."
        
        # Extract as XML
        extract_result = run_cli_command(["uv", "run", "ccore", "-f", "xml", text])
        assert extract_result.returncode == 0
        
        # Verify XML output
        root = ET.fromstring(extract_result.stdout.strip())
        content_elem = root.find(".//content")
        assert content_elem is not None
        assert text in content_elem.text
        
        # Process XML content through clean and summarize
        clean_result = run_cli_command(["uv", "run", "cclean"], input_data=extract_result.stdout)
        assert clean_result.returncode == 0
        
        summary_result = run_cli_command(["uv", "run", "csum", "--context", "one sentence"], input_data=clean_result.stdout)
        assert summary_result.returncode == 0