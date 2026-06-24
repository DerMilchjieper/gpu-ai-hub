import unittest
from hub.db import password_hash,password_ok
from hub.discovery import validate_base_url,validate_network
from hub.hardware import recommend
class CoreTests(unittest.TestCase):
    def test_password_roundtrip(self):
        encoded=password_hash("correct horse battery staple")
        self.assertTrue(password_ok("correct horse battery staple",encoded))
        self.assertFalse(password_ok("wrong",encoded))
    def test_discovery_rejects_large_and_public_networks(self):
        with self.assertRaises(ValueError):validate_network("192.168.0.0/16")
        with self.assertRaises(ValueError):validate_network("8.8.8.0/24")
    def test_service_url_policy(self):
        self.assertEqual(validate_base_url("http://192.168.1.8:11434"),"http://192.168.1.8:11434")
        with self.assertRaises(ValueError):validate_base_url("file:///etc/passwd")
        with self.assertRaises(ValueError):validate_base_url("https://example.com")
    def test_mixed_gpu_recommendation(self):
        result=recommend([{"id":"big","vendor":"nvidia","memory_mib":24576},{"id":"small","vendor":"nvidia","memory_mib":10240}])
        self.assertEqual(result["topology"],"heterogeneous")
        self.assertEqual(result["placements"][0]["accelerator_id"],"big")
if __name__=="__main__":unittest.main()
