import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.mcp_client import MCPClient


class _MCPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if payload.get("method") == "tools/list":
            result = [{"name": "redis_info", "risk": "READ_ONLY"}]
        elif payload.get("method") == "tools/call":
            result = {"name": payload["params"]["name"], "ok": True}
        else:
            result = None
        body = json.dumps({"jsonrpc": "2.0", "id": payload.get("id"), "result": result}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


class MCPClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _MCPHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_list_tools(self):
        client = MCPClient(f"http://127.0.0.1:{self.port}")
        tools = client.list_tools()
        self.assertEqual(tools[0]["name"], "redis_info")

    def test_call_tool(self):
        client = MCPClient(f"http://127.0.0.1:{self.port}")
        result = client.call_tool("redis_info", {"command": "info"})
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
