import asyncio

from content_core.common import ProcessSourceState
from content_core.logging import logger


async def extract_txt(state: ProcessSourceState):
    """
    Parse the text file and extract its content asynchronously.
    """
    return_dict = {}
    if state.file_path is not None and state.identified_type == "text/plain":
        logger.debug(f"Extracting text from {state.file_path}")
        file_path = state.file_path

        if file_path is not None:
            try:

                def _read_file():
                    with open(file_path, "r", encoding="utf-8") as file:
                        return file.read()

                # Run file I/O in thread pool
                content = await asyncio.get_event_loop().run_in_executor(
                    None, _read_file
                )

                logger.debug(f"Extracted: {content[:100]}")
                return_dict["content"] = content

            except FileNotFoundError:
                raise FileNotFoundError(f"File not found at {file_path}")
            except Exception as e:
                raise Exception(f"An error occurred: {e}")

    return return_dict
