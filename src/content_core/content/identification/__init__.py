from .file_detector import FileDetector


async def get_file_type(file_path: str) -> str:
    """
    Identify the file using pure Python file detection
    """
    detector = FileDetector()
    return await detector.detect(file_path)
