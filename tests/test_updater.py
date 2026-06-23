import importlib.util
import unittest
from pathlib import Path

script = Path(__file__).resolve().parents[1] / "scripts" / "update_updates.py"
spec = importlib.util.spec_from_file_location("updater", script)
updater = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(updater)


class UpdaterTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(updater.normalize("Christopher Künneth"), "christopher kunneth")

    def test_author_selection(self):
        researcher = {"name": "Rampi Ramprasad", "institution_tokens": ["georgia tech"]}
        candidates = [{"display_name": "Rampi Ramprasad", "works_count": 200, "last_known_institutions": [{"display_name": "Georgia Institute of Technology"}]}]
        selected, score = updater.select_author(researcher, candidates)
        self.assertEqual(selected["display_name"], "Rampi Ramprasad")
        self.assertGreaterEqual(score, 15)

    def test_relevance(self):
        work = {"title": "Machine learning for generative polymer property prediction", "concepts": [], "topics": []}
        self.assertGreaterEqual(updater.relevance_score(work), 10)

    def test_doi_url(self):
        self.assertEqual(updater.work_url({"doi": "https://doi.org/10.1000/example"}), "https://doi.org/10.1000/example")


if __name__ == "__main__":
    unittest.main()
