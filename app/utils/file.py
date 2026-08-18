"""Lit Review Document File Utility"""

# *** imports

# ** core
from pathlib import Path

# ** app
from tiferet.utils import FileLoader

from ..interfaces.file import DocumentFileService

# *** utils

# ** util: document_file_loader
class DocumentFileLoader(DocumentFileService):
    '''
    Filesystem loader for source-document bytes.

    Wraps FileLoader so attach and download stay on raw bytes and never
    parse or OCR the file.
    '''

    # * method: read_bytes
    def read_bytes(self, path: str) -> bytes:
        '''
        Read the raw bytes at a filesystem path.

        :param path: The file path to read.
        :type path: str
        :return: The file contents.
        :rtype: bytes
        '''

        # Open the upload as binary and return its body.
        with FileLoader(path, mode='rb') as file:
            return file.read()

    # * method: write_bytes
    def write_bytes(self, path: str, data: bytes) -> None:
        '''
        Write raw bytes to a filesystem path.

        :param path: The file path to write.
        :type path: str
        :param data: The bytes to persist.
        :type data: bytes
        '''

        # Ensure the destination directory exists before opening for write.
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        # Write the document bytes under the API name.
        with FileLoader(path, mode='wb') as file:
            file.write(data)
