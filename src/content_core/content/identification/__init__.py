import magic


async def get_file_type(file_path: str) -> str:
    """
    Identify the file using python-magic
    """
    return magic.from_file(file_path, mime=True)
