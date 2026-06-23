import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update_updates.py"
spec = importlib.util.spec_from_file_location("updater", SCRIPT)
updater = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(updater)


class UpdateTests(unittest.TestCase):
    def test_normalize_removes_accents_and_punctuation(self):
        self.assertEqual(updater.normalize("Christopher Künneth"), "christopher kunneth")

    def test_select_author_prefers_exact_name_and_institution(self):
        researcher = {"name": "Rampi Ramprasad", "institution_tokens": ["georgia tech"]}
        candidates = [
            {"display_name": "Rampi Ramprasad", "works_count": 200, "last_known_institutions": [{"display_name": "Georgia Institute of Technology"}]},
            {"display_name": "R. Ramprasad", "works_count": 400, "last_known_institutions": [{"display_name": "Elsewhere"}]},
        ]
        selected, score = updater.select_author(researcher, candidates)
        self.assertEqual(selected["display_name"], "Rampi Ramprasad")
        self.assertGreaterEqual(score, 15)

    def test_relevance_score_rewards_polymer_ai_terms(self):
        work = {"title": "Machine learning for generative polymer property prediction", "concepts": [], "topics": []}
        self.assertGreaterEqual(updater.relevance_score(work), 10)

    def test_work_url_prefers_doi(self):
        self.assertEqual(updater.work_url({"doi": "https://doi.org/10.1000/test"}), "https://doi.org/10.1000/test")

    def test_low_confidence_author_is_rejected(self):
        researcher = {"name": "A Unique Name", "institution_tokens": ["target university"]}
        selected, _ = updater.select_author(researcher, [{"display_name": "Different Person", "works_count": 50, "last_known_institutions": []}])
        self.assertIsNone(selected)


if __name__ == "__main__":
    unittest.main()
