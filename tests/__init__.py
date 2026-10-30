import os
import tempfile

# tests never touch the real ~/.customlab (saved zones)
os.environ.setdefault("CUSTOMLAB_HOME", tempfile.mkdtemp(prefix="customlab_test_home_"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CUSTOMLAB_SYNC", "1")                 # GUI tests are deterministic; the async path has its own tests
