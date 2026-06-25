import json,unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]
class ConfigTests(unittest.TestCase):
    def test_supported_locales_are_complete(self):
        locales=sorted(path.name for path in (ROOT/"locales").glob("*.json"))
        self.assertEqual(locales,["de.json","en.json","es.json","fr.json"])
        english=json.loads((ROOT/"locales/en.json").read_text())
        self.assertTrue(english)
        for locale in locales:
            labels=json.loads((ROOT/"locales"/locale).read_text())
            self.assertEqual(set(labels),set(english),locale)
            self.assertTrue(all(isinstance(value,str) and value for value in labels.values()),locale)
    def test_service_ids_unique(self):
        services=json.loads((ROOT/"config/services.json").read_text())
        ids=[x["id"] for x in services]
        self.assertEqual(len(ids),len(set(ids)))
    def test_workflow_titles_are_english_strings(self):
        workflows=json.loads((ROOT/"config/comfyui.json").read_text())["workflows"]
        self.assertTrue(workflows)
        self.assertTrue(all(isinstance(workflow["title"],str) for workflow in workflows))
    def test_models_have_pullable_names(self):
        profiles=json.loads((ROOT/"config/models.json").read_text())
        self.assertIn("minimal",profiles)
        for models in profiles.values():
            for model in models:self.assertTrue(model["model"] and " " not in model["model"])
if __name__=="__main__":unittest.main()
