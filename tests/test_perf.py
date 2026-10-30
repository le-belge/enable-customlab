import math
import unittest

import numpy as np

from customlab import deco


class Raster(unittest.TestCase):
    def _random_mesh(self, n=4000, seed=1):
        rng = np.random.default_rng(seed); c = rng.uniform(0, 40, (n, 1, 3)); return c + rng.uniform(-0.6, 0.6, (n, 3, 3))      # small triangles + a few big ones

    def _both(self, P, res=0.25):
        lo, hi = P.reshape(-1, 3).min(0), P.reshape(-1, 3).max(0); u0, v0 = lo[0] - 2, lo[1] - 2
        nu, nv = int(math.ceil((hi[0] - lo[0] + 4) / res)) + 1, int(math.ceil((hi[1] - lo[1] + 4) / res)) + 1
        A = np.full((nu, nv), -np.inf); B = A.copy()
        deco._raster_loop(P, A, u0, v0, res, nu, nv)
        su = (P[:, :, 0].max(1) - P[:, :, 0].min(1)) / res; sv = (P[:, :, 1].max(1) - P[:, :, 1].min(1)) / res; small = (su <= 1.9) & (sv <= 1.9)
        deco._raster_small(P[small], B, u0, v0, res, nu, nv); deco._raster_loop(P[~small], B, u0, v0, res, nu, nv)
        return A, B, int(small.sum())

    def test_vectorised_raster_equals_the_reference_loop(self):
        P = self._random_mesh(); P[:30] *= 1.0; P[:30, 1] += 12                      # include some large triangles
        A, B, n_small = self._both(P); self.assertGreater(n_small, 100)
        self.assertTrue(np.array_equal(np.isinf(A), np.isinf(B))); self.assertLess(float(np.abs(A[~np.isinf(A)] - B[~np.isinf(B)]).max()), 1e-9)

    def test_equivalence_on_degenerate_and_axis_aligned_triangles(self):
        P = np.array([[[0, 0, 1], [1, 0, 1], [0, 1, 1]], [[0, 0, 2], [2, 0, 2], [4, 0, 2]], [[1, 1, 3], [1.2, 1, 3], [1, 1.2, 3]], [[5, 5, 1], [5, 5, 1], [5, 5, 1]]], float)
        A, B, _ = self._both(P, 0.25); self.assertTrue(np.array_equal(np.isinf(A), np.isinf(B))); self.assertLess(float(np.abs(A[~np.isinf(A)] - B[~np.isinf(B)]).max()), 1e-9)

    def test_fine_mesh_is_fast_enough(self):
        import time
        n = 250000; rng = np.random.default_rng(3); c = rng.uniform(0, 100, (n, 1, 3)); P = c + rng.uniform(-0.2, 0.2, (n, 3, 3))
        t = time.time(); hm = deco.build_heightmap(P.reshape(-1, 3).tolist() if False else P, "+z", 0.25); self.assertLess(time.time() - t, 8.0)   # was ~30 s with the per-triangle loop
        self.assertGreater(float(np.nanmax(hm.H)), 0.0)


if __name__ == "__main__":
    unittest.main()
