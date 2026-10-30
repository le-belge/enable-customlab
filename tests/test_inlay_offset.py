import unittest
from customlab import deco


class InlayOffset(unittest.TestCase):
    def test_default_unchanged(self):
        self.assertEqual(deco.DecoSpec().inlay_offset_mm, deco.INLAY_TOP_OFFSET_MM)

    def test_out_of_range_is_refused_not_clamped(self):
        import tempfile, pathlib
        from customlab.deco import DecoSpec, DecoError, apply_decoration
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "cube.stl"; deco.write_stl(p, deco.build_box_tris(10, 10, 10) if hasattr(deco, "build_box_tris") else [((0, 0, 0), (1, 0, 0), (0, 1, 0))])
            with self.assertRaisesRegex(DecoError, "hors plage"):
                apply_decoration(p, DecoSpec(kind="text", text="A", mode="inlay", inlay_offset_mm=deco.INLAY_OFFSET_RANGE[1] + 0.01))


if __name__ == "__main__": unittest.main()
