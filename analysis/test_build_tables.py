"""Run with: python3 -m unittest discover -s analysis -v."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from build_tables import (
    ROOT, average_configs, build_runs, check_runs, peak_concurrency,
    percentile, summarize_run,
)


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = build_runs(ROOT)

    def test_all_rounds_and_guide_references(self):
        self.assertEqual(len(self.runs), 33)
        self.assertEqual(sum(r["requests"] for r in self.runs), 102119)
        references = {
            "api-512": (9601, 37.2, 43.1, 80.0, 1.9, 0.22, 2.97),
            "cpu-1024": (292, 1234.0, 1287.5, 2.43, 1192.0, 20.1, 3.00),
            "cpu-1024-high": (787, 1219.2, 1264.1, 6.56, 1178.2, 19.9, 8.00),
            "data-512": (243, 1481.4, 1585.4, 2.02, 1435.9, 12.2, 3.00),
        }
        columns = ["requests", "mean_ms", "p95_ms", "throughput_rps", "exec_mean_ms",
                   "cost_per_million_usd", "littles_law"]
        for run in self.runs:
            self.assertEqual(run["failure_rate"], 0)
            if run["round"] != 1:
                continue
            self.assertEqual(run["cold_starts"], int(run["setup"] == "api-512"))
            if run["setup"] in references:
                for column, expected in zip(columns, references[run["setup"]]):
                    with self.subTest(setup=run["setup"], column=column):
                        tolerance = 0 if column == "requests" else 0.1
                        self.assertAlmostEqual(run[column], expected, delta=tolerance)
        self.assertFalse(any(r["flag"] for r in check_runs(self.runs)))

    def test_setup_averages_give_rounds_equal_weight(self):
        first = dict(self.runs[0], round=1, requests=1, mean_ms=10)
        second = dict(first, round=2, requests=1000, mean_ms=30)
        result = average_configs([first, second])
        self.assertEqual(result[0]["mean_ms"], 20)
        self.assertEqual(len(average_configs(self.runs)), 11)

    def test_percentiles(self):
        self.assertEqual(percentile([10, 20, 30, 40], 0.95), 38.5)
        self.assertEqual(percentile([7], 0.99), 7)

    def test_minute_overlap_excludes_other_runs(self):
        metrics = {"period_seconds": 60, "metrics": {"ConcurrentExecutions_Maximum": {
            "timestamps": ["1970-01-01T00:00:00+00:00", "1970-01-01T00:01:00+00:00",
                           "1970-01-01T00:02:00+00:00"],
            "values": [99, 3, 88],
        }}}
        self.assertEqual(peak_concurrency(metrics, [{"t": 61000, "duration_ms": 100}]), 3)
        # The last response extends across a minute boundary.
        self.assertEqual(peak_concurrency(metrics, [{"t": 119900, "duration_ms": 200}]), 88)
        with self.assertRaisesRegex(ValueError, "No concurrency metrics"):
            peak_concurrency(metrics, [{"t": 200000, "duration_ms": 1}])

    def test_failure_types_cost_and_sample_standard_deviation(self):
        requests = [
            {"request_id": str(i), "t": 61000, "duration_ms": duration,
             "status": status, "valid": valid, "cold": i == 0}
            for i, (status, valid, duration) in enumerate([
                (200, True, 10), (429, False, 20), (503, False, 30),
                (504, False, 40), (0, False, 50), (200, False, 60), (403, False, 70),
            ])
        ]
        aws = {r["request_id"]: {
            "memory_mb": "1024", "duration_ms": "5", "billed_ms": "6",
            "max_memory_used_mb": "32", "status": "timeout" if i == 3 else "",
        } for i, r in enumerate(requests)}
        metrics = {"period_seconds": 60, "metrics": {"ConcurrentExecutions_Maximum": {
            "timestamps": ["1970-01-01T00:01:00+00:00"], "values": [3],
        }}}
        row = summarize_run(1, "cpu-1024", 3, requests, aws, metrics)
        self.assertEqual([row[k] for k in ("throttled", "function_errors", "timeouts",
                                          "wrong_answers", "successful")], [1, 1, 2, 1, 1])
        self.assertEqual(row["throughput_rps"], 1 / 120)
        self.assertAlmostEqual(row["failure_rate"], 6 / 7)
        self.assertAlmostEqual(row["std_ms"], (2800 / 6) ** 0.5)
        self.assertEqual(row["overhead_ms"], 35)
        self.assertAlmostEqual(row["cost_per_million_usd"], 0.3000002)
        check = check_runs([row])[0]
        self.assertTrue(check["flag"])
        self.assertEqual(check["other_failures"], 1)
        self.assertEqual(check["cold_starts"], 1)

    def test_check_boundary_and_cold_starts(self):
        row = dict(self.runs[0], users=10, littles_law=11, cold_starts=1)
        self.assertFalse(check_runs([row])[0]["flag"])
        row["littles_law"] = 11.01
        self.assertTrue(check_runs([row])[0]["flag"])

    def test_input_validation_and_warmup_exclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "config/experiment.json").write_text((ROOT / "config/experiment.json").read_text())
            k6 = root / "results/round1/k6-measured-data"
            aws = root / "results/round1/aws-export-data"
            k6.mkdir(parents=True)
            aws.mkdir()
            reports = {}
            for source in (ROOT / "results/round1/k6-measured-data").glob("*.jsonl"):
                measured = next(json.loads(line) for line in source.read_text().splitlines()
                                if json.loads(line)["phase"] == "measure")
                warmup = dict(measured, phase="warmup", duration_ms=999999)
                (k6 / source.name).write_text(json.dumps(warmup) + "\n" + json.dumps(measured) + "\n")
                function = "-".join(measured["setup"].split("-")[:2])
                reports.setdefault(function, []).append(measured["request_id"])
            for function, ids in reports.items():
                source = ROOT / "results/round1/aws-export-data" / f"seng533-{function}.report.csv"
                with source.open(newline="") as stream:
                    reader = csv.DictReader(stream)
                    columns = reader.fieldnames
                    selected = [r for r in reader if r["request_id"] in ids]
                with (aws / source.name).open("w", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=columns)
                    writer.writeheader()
                    writer.writerows(selected)
                name = f"seng533-{function}.metrics.json"
                (aws / name).write_text((ROOT / "results/round1/aws-export-data" / name).read_text())
            runs = build_runs(root)
            self.assertEqual(len(runs), 11)
            self.assertTrue(all(r["requests"] == 1 and r["std_ms"] == 0 for r in runs))

            path = next(k6.glob("*.jsonl"))
            original = path.read_text()
            measured = json.loads(original.splitlines()[-1])
            path.write_text(original + json.dumps(measured) + "\n")
            with self.assertRaisesRegex(ValueError, "duplicate measured request_id"):
                build_runs(root)
            measured["request_id"] = "missing-aws-id"
            path.write_text(original.splitlines()[0] + "\n" + json.dumps(measured) + "\n")
            with self.assertRaisesRegex(ValueError, "no AWS record"):
                build_runs(root)
            path.write_text(original)

            report = next(aws.glob("*.report.csv"))
            original_report = report.read_text()
            report.write_text(original_report + original_report.splitlines()[-1] + "\n")
            with self.assertRaisesRegex(ValueError, "duplicate AWS request_id"):
                build_runs(root)
            report.write_text(original_report)
            path.unlink()
            with self.assertRaisesRegex(ValueError, "exactly one JSONL"):
                build_runs(root)


if __name__ == "__main__":
    unittest.main()
