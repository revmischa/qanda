import asyncio
import asyncio.queues
import logging

import websockets
from websockets.exceptions import (PayloadTooBig,
                         WebSocketProtocolError)
from websockets.protocol import WebSocketCommonProtocol

logger = logging.getLogger(__name__)


class WebSocketProtocol(WebSocketCommonProtocol):

    def __init__(self, loop):
        super().__init__(loop=loop)

    async def run(self):
        # This coroutine guarantees that the connection is closed at exit.
        await self.opening_handshake
        while not self.closing_handshake.done():
            try:
                msg = await self.read_message()
                if msg is None:
                    break
                await self.messages.put(msg)
                await self.message_received(await self.messages.get())

            except asyncio.CancelledError:
                break
            except WebSocketProtocolError:
                await self.fail_connection(1002)
            except asyncio.IncompleteReadError:
                await self.fail_connection(1006)
            except UnicodeDecodeError:
                await self.fail_connection(1007)
            except PayloadTooBig:
                await self.fail_connection(1009)
            except Exception:
                await self.fail_connection(1011)
                raise
        await self.close_connection()

    async def message_received(self, message):
        raise NotImplementedError


class WebSocketHandshakeResponse(list):

    def __init__(self, environ):
        self.headers = []
        self.environ = environ
        self.status = '101 Switching Protocols'

        websocket_key = websockets.handshake.check_request(self.get_request_header)
        websockets.handshake.build_response(self.set_response_header, websocket_key)

    def get_request_header(self, key):
        return self.environ.get('HTTP_' + key.upper().replace('-', '_'), '')

    def set_response_header(self, key, value):
        self.headers.append((key, value))