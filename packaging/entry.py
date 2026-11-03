"""Entry point of the packaged app (PyInstaller). `--selftest [--report FILE]`: checks without any window, exit code 0/1."""
import sys

if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        from customlab.selftest import main as selftest
        raise SystemExit(selftest())
    from customlab.gui import main
    raise SystemExit(main())
