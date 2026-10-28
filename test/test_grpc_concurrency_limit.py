"""gRPC server từ chối RPC vượt AI_GRPC_MAXIMUM_CONCURRENT_RPCS bằng RESOURCE_EXHAUSTED (bug-046)."""
import asyncio
import unittest

import grpc
from grpc import aio

from app.config.server_config import ServerConfig
from app.grpc_server import build_server

_METHOD = "/test.Slow/Call"


class _SlowHandler(grpc.GenericRpcHandler):
    def __init__(self, release: asyncio.Event):
        self._release = release

    def service(self, handler_call_details):
        if handler_call_details.method != _METHOD:
            return None

        async def call(request, context):
            await self._release.wait()
            return b"ok"

        return grpc.unary_unary_rpc_method_handler(call)


class GrpcConcurrencyLimitTest(unittest.IsolatedAsyncioTestCase):
    async def test_rpc_vuot_tran_nhan_resource_exhausted(self):
        release = asyncio.Event()
        server = build_server(ServerConfig(grpc_maximum_concurrent_rpcs=1))
        server.add_generic_rpc_handlers((_SlowHandler(release),))
        port = server.add_insecure_port("127.0.0.1:0")
        await server.start()
        try:
            async with aio.insecure_channel(f"127.0.0.1:{port}") as channel:
                call = channel.unary_unary(_METHOD)
                first = asyncio.ensure_future(call(b"x", timeout=5))
                await asyncio.sleep(0.2)  # cho RPC đầu chiếm chỗ duy nhất

                with self.assertRaises(aio.AioRpcError) as ctx:
                    await call(b"x", timeout=5)
                self.assertEqual(ctx.exception.code(), grpc.StatusCode.RESOURCE_EXHAUSTED)

                release.set()
                self.assertEqual(await first, b"ok")
        finally:
            await server.stop(grace=0)

    def test_tran_mac_dinh_hop_le(self):
        self.assertGreaterEqual(ServerConfig().grpc_maximum_concurrent_rpcs, ServerConfig().grpc_max_workers)
        with self.assertRaises(ValueError):
            ServerConfig(grpc_maximum_concurrent_rpcs=0)


if __name__ == "__main__":
    unittest.main()
