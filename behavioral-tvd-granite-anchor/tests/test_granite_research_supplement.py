"""Offline-only checks of the new supplementary analysis, not frozen inference."""
import importlib.util
import math
from pathlib import Path
import socket
import tempfile
import unittest

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/analyze_granite_research_supplement.py'
spec = importlib.util.spec_from_file_location('research_supplement', SCRIPT)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def response(lp0=-1.0, lp1=-0.6):
    return {'choices': [{'logprobs': {'content': [
        {'token': '1', 'bytes': [49], 'logprob': lp1, 'top_logprobs': [
            {'token': '0', 'bytes': [48], 'logprob': lp0},
            {'token': '1', 'bytes': [49], 'logprob': lp1}]}]}}]}


class ResearchSupplementTests(unittest.TestCase):
    def test_raw_probabilities_and_swapped_semantic_orientation(self):
        p, logs, mass = analysis.raw_semantic(response(), False)
        swapped, _, _ = analysis.raw_semantic(response(), True)
        self.assertAlmostEqual(mass, math.exp(-1) + math.exp(-.6))
        self.assertEqual(logs, {'0': -1., '1': -.6})
        self.assertAlmostEqual(p, math.exp(-.6) / mass)
        self.assertAlmostEqual(swapped, 1 - p)
        self.assertNotEqual(p, 1)  # Returned sampled token is not the measurement.

    def test_missing_or_malformed_logprobs_are_rejected(self):
        malformed = [
            {'choices': [{'logprobs': None}]},
            {'choices': [{'logprobs': {'content': []}}]},
            response(float('nan'), -.6), response(-1000, -.6), response(0, 0),
        ]
        only_one = response()
        only_one['choices'][0]['logprobs']['content'][0]['top_logprobs'] = []
        malformed.append(only_one)
        wrong_byte = response()
        wrong_byte['choices'][0]['logprobs']['content'][0]['top_logprobs'][0]['bytes'] = [49]
        malformed.append(wrong_byte)
        conflict = response()
        conflict['choices'][0]['logprobs']['content'][0]['top_logprobs'][1]['logprob'] = -.8
        malformed.append(conflict)
        for value in malformed:
            with self.subTest(value=value), self.assertRaises(ValueError):
                analysis.raw_semantic(value, False)

    def test_one_missing_probability_excludes_entire_common_scenario(self):
        p = np.full((4, 24, 3), .5)
        baseline = np.full((4, 3), .5)
        p[1, 22, 1] = np.nan
        self.assertEqual(analysis.complete_mask(p, baseline).tolist(), [True, False, True])
        baseline[0, 2] = np.nan
        self.assertEqual(analysis.complete_mask(p, baseline).tolist(), [True, False, False])
        with self.assertRaises(ValueError):
            analysis.calculate(p)

    def test_averaging_vectors_is_not_averaging_distances(self):
        p = np.array([[[0.], [1.]], [[1.], [0.]], [[0.], [1.]], [[1.], [0.]]])
        q, distances, proof = analysis.calculate(p)
        np.testing.assert_array_equal(q, [[.5], [.5]])
        self.assertEqual(distances['A_primary'][0, 1], 0.)
        self.assertEqual(distances['B_secondary'][0, 1], 1.)
        self.assertEqual(distances['C_canonical'][0, 1], 1.)
        self.assertTrue(proof['A_le_B'])
        # Pseudometric can identify distinct condition-specific profiles.
        np.testing.assert_array_equal(distances['A_primary'], np.zeros((2, 2)))

    def test_ranks_use_unrounded_values_and_explicit_ties(self):
        d = np.array([[0., .1, .10000000001], [.1, 0., .1], [.10000000001, .1, 0.]])
        ranks = analysis.ranked_pairs(d, ['a', 'b', 'c'])
        self.assertEqual([r['rank_closest_first'] for r in ranks], [1, 1, 3])
        self.assertEqual([r['rank_max_if_tied'] for r in ranks], [2, 2, 3])
        self.assertEqual([r['ordinal_rank_id_tiebreak'] for r in ranks], [1, 2, 3])

    def test_protect_existing_scientific_artifacts(self):
        root = SCRIPT.parents[1]
        for path in [root, root / 'data', root / 'configs',
                     root / 'results/granite-exploratory/cumulative-through-0011', root.parent]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                analysis.validated_output(path)
        self.assertEqual(analysis.validated_output(root / analysis.DEFAULT_OUT), (root / analysis.DEFAULT_OUT).resolve())
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(analysis.validated_output(directory), Path(directory).resolve())

    def test_offline_guard_prevents_connections(self):
        with analysis.no_network():
            with self.assertRaisesRegex(RuntimeError, 'Offline analysis'):
                socket.create_connection(('example.invalid', 443))
            with socket.socket() as connection:
                with self.assertRaisesRegex(RuntimeError, 'Offline analysis'):
                    connection.connect(('127.0.0.1', 443))


if __name__ == '__main__':
    unittest.main()
