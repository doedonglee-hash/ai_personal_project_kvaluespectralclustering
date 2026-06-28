import importlib
import os
import sys
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from build_features import build_feature_table
from clean_literature_dataset import parse_numeric_like
from validate_dataset import validate_dataframe


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.seed_path = PROJECT_ROOT / "data" / "raw" / "click_reaction_seed.csv"
        self.seed = pd.read_csv(self.seed_path)

    def test_seed_dataset_has_no_validation_errors(self):
        errors, warnings = validate_dataframe(self.seed)
        self.assertEqual(errors, [])
        self.assertTrue(any("not primary_checked" in warning for warning in warnings))

    def test_feature_builder_creates_log_target(self):
        features = build_feature_table(self.seed)
        self.assertIn("log10_k", features.columns)
        self.assertEqual(len(features), len(self.seed))
        self.assertTrue(features["log10_k"].notna().all())

    def test_package_imports_work(self):
        for module_name in [
            "src.validate_dataset",
            "src.build_features",
            "src.run_analysis",
            "src.fetch_pubchem_smiles",
        ]:
            module = importlib.import_module(module_name)
            self.assertIsNotNone(module)

    def test_project_relative_paths_resolve_from_notebooks_directory(self):
        from src.click_reaction_config import resolve_project_path

        previous_cwd = Path.cwd()
        try:
            os.chdir(PROJECT_ROOT / "notebooks")
            resolved = resolve_project_path("data/raw/click_reaction_seed.csv", must_exist=True)
            self.assertEqual(resolved, self.seed_path.resolve())
        finally:
            os.chdir(previous_cwd)

    def test_literature_numeric_parser_handles_llm_extractions(self):
        self.assertAlmostEqual(parse_numeric_like("4.3 × 10-3"), 0.0043)
        self.assertAlmostEqual(parse_numeric_like("(9.0 ± 0.3) × 10-2"), 0.09)
        self.assertEqual(parse_numeric_like(">95"), 95.0)


if __name__ == "__main__":
    unittest.main()
