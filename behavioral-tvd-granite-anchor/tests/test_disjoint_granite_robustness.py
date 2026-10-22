from pathlib import Path
import sys
import unittest

import numpy as np

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
from disjoint_granite_robustness import compare


class DisjointRobustnessTests(unittest.TestCase):
    def test_disjoint_geometry_is_not_nested_stability(self):
        q=[[0,0,1,1],[0,1,0,0],[1,1,1,0]]
        matrices,_,s=compare(q,['a','b','c'],['s1','s2','s3','s4'])
        np.testing.assert_array_equal(matrices[0],[[0,.5,1],[.5,0,.5],[1,.5,0]])
        np.testing.assert_array_equal(matrices[1],[[0,1,.5],[1,0,.5],[.5,.5,0]])
        self.assertAlmostEqual(s['primary_A_distance_spearman'],-.5)
        self.assertAlmostEqual(s['mean_absolute_normalized_distance_difference'],1/3)
        self.assertEqual(s['nearest_neighbor_agreement_count'],0)
        self.assertEqual(s['scenario_overlap_count'],0)

    def test_missing_probability_is_not_imputed(self):
        with self.assertRaises(ValueError):compare([[0,0,1,float('nan')],[0,1,0,0],[1,1,1,0]],['a','b','c'],['1','2','3','4'])

    def test_shared_identity_is_not_called_disjoint(self):
        with self.assertRaises(ValueError):compare([[0,0,1,1],[0,1,0,0],[1,1,1,0]],['a','b','c'],['1','2','1','4'])
