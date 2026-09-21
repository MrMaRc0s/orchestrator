import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from app.health import start_health_server


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.server = start_health_server(port=0)
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_health_endpoint_is_available(self):
        with urlopen(f"{self.base_url}/healthz", timeout=2) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b"OK")

    def test_no_billing_http_endpoint_is_exposed(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(f"{self.base_url}/api/billing", timeout=2)
        self.assertEqual(error.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
