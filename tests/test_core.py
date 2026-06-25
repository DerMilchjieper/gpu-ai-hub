import unittest
from hub.db import password_hash,password_ok
from hub.discovery import validate_base_url,validate_network
from hub.hardware import model_recommendations,recommend
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
    def test_model_recommendation_uses_largest_vram_profile(self):
        profiles={"cpu":[{"model":"small","min_memory_gib":4}],"minimal":[{"model":"mid","min_memory_gib":8}],"large":[{"model":"big","min_memory_gib":22}]}
        inv={"cpu_count":8,"memory_mib":32768,"accelerators":[{"vendor":"nvidia","name":"RTX","backend":"cuda","memory_mib":24576}]}
        result=model_recommendations(inv,profiles)
        self.assertEqual(result["selected_profile"],"large")
    def test_model_recommendation_has_cpu_fallback(self):
        profiles={"cpu":[{"model":"small","min_memory_gib":4}],"minimal":[{"model":"mid","min_memory_gib":12}]}
        inv={"cpu_count":8,"memory_mib":16384,"accelerators":[]}
        result=model_recommendations(inv,profiles)
        self.assertEqual(result["selected_profile"],"cpu")
if __name__=="__main__":unittest.main()
