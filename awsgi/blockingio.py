import io

import time


class BlockingIO(io.BytesIO):

    def __init__(self, initial_bytes=None):
        super().__init__(initial_bytes)
        self.got_eof = False
        self.read_pos = 0

    def readline(self, size=-1):
        self.seek(self.read_pos)

        result = None
        while not result:
            # time.sleep(1)
            if self.got_eof:
                return b''

            result = super().readline(size)

        self.read_pos += len(result)

        return result

    def read(self, size=-1):
        self.seek(self.read_pos)

        result = None
        while not result:
            # time.sleep(1)
            if self.got_eof:
                return b''

            result = super().read(size)

        self.read_pos += len(result)

        return result

    def feed_eof(self):
        self.got_eof = True