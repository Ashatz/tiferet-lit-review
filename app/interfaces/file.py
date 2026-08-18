"""Lit Review Document File Interface"""

# *** imports

# ** core
from abc import abstractmethod

# ** app
from tiferet.interfaces.core import Service

# *** interfaces

# ** interface: document_file_service
class DocumentFileService(Service):
    '''
    Vertical interface for reading and writing raw source-document bytes.
    '''

    # * method: read_bytes
    @abstractmethod
    def read_bytes(self, path: str) -> bytes:
        '''
        Read the raw bytes at a filesystem path.

        :param path: The file path to read.
        :type path: str
        :return: The file contents.
        :rtype: bytes
        '''
        raise NotImplementedError()

    # * method: write_bytes
    @abstractmethod
    def write_bytes(self, path: str, data: bytes) -> None:
        '''
        Write raw bytes to a filesystem path.

        :param path: The file path to write.
        :type path: str
        :param data: The bytes to persist.
        :type data: bytes
        '''
        raise NotImplementedError()
