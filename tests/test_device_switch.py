import os, unittest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from customlab import gui

_app = QApplication.instance() or QApplication([])


class DeviceSwitch(unittest.TestCase):
    def test_pending_load_is_dropped_when_device_changes(self):
        w = gui.MainWindow(); w.select("kinetic_hand")
        c = w.custom; gen = c._lgen + 1; c._lgen = gen; c._pending_path = "/nonexistent/kinetic.stl"     # a Kinetic load is in flight
        w.select("phoenix_hand")
        c._on_loaded(gen, ("ok", None))                                                                  # its result arrives late
        self.assertIsNone(c.part_path)
        self.assertTrue(c.lib.isEnabled())


if __name__ == "__main__": unittest.main()
