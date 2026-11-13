"""A busy IPv6 port must not stop IPv4 when the resolver lists IPv6 first."""

import errno
import importlib.util
import socket
import unittest
from pathlib import Path
from unittest.mock import patch

_SOURCE = Path(__file__).parents[3] / "src/ha_mcp/listen_sockets.py"
_SPEC = importlib.util.spec_from_file_location("listen_sockets_order_ut", _SOURCE)
assert _SPEC is not None and _SPEC.loader is not None
listen_sockets = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(listen_sockets)


class ListenSocketAddressOrderTests(unittest.TestCase):
    def test_busy_ipv4_is_reported_with_either_resolver_order(self):
        getaddrinfo = socket.getaddrinfo
        for first_family in (socket.AF_INET, socket.AF_INET6):
            with (
                self.subTest(first_family=first_family),
                socket.socket(socket.AF_INET, socket.SOCK_STREAM) as taken,
            ):
                taken.bind(("0.0.0.0", 0))
                taken.listen()
                port = taken.getsockname()[1]
                addresses = getaddrinfo(
                    None,
                    port,
                    socket.AF_UNSPEC,
                    socket.SOCK_STREAM,
                    0,
                    socket.AI_PASSIVE,
                )
                addresses.sort(key=lambda address: address[0] != first_family)
                with (
                    patch.object(socket, "getaddrinfo", return_value=addresses),
                    self.assertRaises(OSError) as raised,
                ):
                    listen_sockets.wildcard_listen_sockets("0.0.0.0", port)
                self.assertEqual(raised.exception.errno, errno.EADDRINUSE)

    def test_busy_ipv6_keeps_ipv4_with_either_resolver_order(self):
        getaddrinfo = socket.getaddrinfo
        for first_family in (socket.AF_INET, socket.AF_INET6):
            with self.subTest(first_family=first_family):
                with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as taken:
                    taken.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                    taken.bind(("::", 0))
                    taken.listen()
                    port = taken.getsockname()[1]
                    addresses = getaddrinfo(
                        None,
                        port,
                        socket.AF_UNSPEC,
                        socket.SOCK_STREAM,
                        0,
                        socket.AI_PASSIVE,
                    )
                    addresses.sort(key=lambda address: address[0] != first_family)
                    with patch.object(socket, "getaddrinfo", return_value=addresses):
                        sockets = listen_sockets.wildcard_listen_sockets(
                            "0.0.0.0", port
                        )
                self.assertIsNotNone(sockets)
                try:
                    self.assertEqual([s.family for s in sockets], [socket.AF_INET])
                    sockets[0].listen()
                    with socket.create_connection(("127.0.0.1", port), timeout=2):
                        pass
                finally:
                    for sock in sockets:
                        sock.close()
