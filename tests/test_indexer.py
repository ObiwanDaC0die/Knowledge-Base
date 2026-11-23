import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_index import build_index, discover_documents, extract_metadata, filename_title, stable_id


class IndexerTests(unittest.TestCase):
    def test_filename_title_formats_snake_and_kebab_case(self):
        self.assertEqual(filename_title("federal_policy_review.html"), "Federal Policy Review")
        self.assertEqual(filename_title("water-resources.html"), "Water Resources")

    def test_metadata_extraction_and_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc = root / "sample.html"
            doc.write_text('<title> Sample Resource </title><meta name="description" content="A useful guide."><meta name="tags" content="Planning, Research; planning"><meta name="keywords" content="Corps, formulation"><svg><title>Decorative graphic title</title></svg>', encoding="utf-8")
            data = extract_metadata(doc, "nested/sample.html")
            self.assertEqual(data["title"], "Sample Resource")
            self.assertEqual(data["description"], "A useful guide.")
            self.assertEqual(data["tags"], ["Planning", "Research"])
            self.assertEqual(data["keywords"], ["Corps", "formulation"])
            self.assertEqual(data["id"], stable_id("nested/sample.html"))

    def test_recursive_discovery_is_sorted_and_skips_homepage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text("<title>Home</title>", encoding="utf-8")
            (root / "z_folder").mkdir()
            (root / "a_folder").mkdir()
            (root / "z_folder" / "zulu_topic.html").write_text("<title>Zulu Topic</title>", encoding="utf-8")
            (root / "a_folder" / "alpha_topic.html").write_text('<meta name="description" content="Alpha">', encoding="utf-8")
            docs = discover_documents(root)
            self.assertEqual([doc["title"] for doc in docs], ["Alpha Topic", "Zulu Topic"])
            self.assertEqual(docs[0]["path"], "a_folder/alpha_topic.html")

    def test_ids_are_stable_for_a_path_and_differ_between_paths(self):
        self.assertEqual(stable_id("documents/topic.html"), stable_id("documents/topic.html"))
        self.assertNotEqual(stable_id("documents/topic.html"), stable_id("other/topic.html"))

    def test_build_index_uses_supplied_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "doc.html").write_text("<title>Doc</title>", encoding="utf-8")
            payload = build_index(root, "2026-01-01T00:00:00+00:00")
            self.assertEqual(payload["generatedAt"], "2026-01-01T00:00:00+00:00")
            self.assertEqual(len(payload["documents"]), 1)


if __name__ == "__main__":
    unittest.main()
