import json,unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]
class ConfigTests(unittest.TestCase):
    def test_locales_have_same_keys(self):
        en=json.loads((ROOT/"locales/en.json").read_text())
        de=json.loads((ROOT/"locales/de.json").read_text())
        self.assertEqual(set(en),set(de))
    def test_service_ids_unique(self):
        services=json.loads((ROOT/"config/services.json").read_text())
        ids=[x["id"] for x in services]
        self.assertEqual(len(ids),len(set(ids)))
    def test_models_have_pullable_names(self):
        profiles=json.loads((ROOT/"config/models.json").read_text())
        self.assertIn("minimal",profiles)
        for models in profiles.values():
            for model in models:self.assertTrue(model["model"] and " " not in model["model"])
if __name__=="__main__":unittest.main()
