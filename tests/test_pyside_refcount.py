"""PySide6 6.12.0 releases a reference to None on every call of a Qt method returning void (Python 3.9 to 3.11, where None is not
immortal): the app then aborts with "Fatal Python error: none_dealloc" (CI run 41710497779). Guard against shipping such a version."""
import sys
import unittest

try:
    from PySide6.QtCore import QObject
    HAVE = True
except ImportError:
    HAVE = False


@unittest.skipUnless(HAVE, "PySide6 not installed")
@unittest.skipIf(sys.version_info >= (3, 12), "None is immortal from Python 3.12: its reference count does not move")
class NoneRefcount(unittest.TestCase):
    def test_void_qt_calls_keep_none_alive(self):
        o = QObject(); before = sys.getrefcount(None)
        for _ in range(200): o.setObjectName("x")
        self.assertGreaterEqual(sys.getrefcount(None) - before, -10, "this PySide6 version corrupts the reference count of None: use PySide6-Essentials<6.12")


if __name__ == "__main__":
    unittest.main()
