"""Error journal: <home>/logs/customlab.log (UTF-8, simple rotation) and an excepthook that logs the trace and tells the user.

The packaged app has no console (console=False), so without this an unexpected error leaves no trace at all. The dialog offers
"Copier le rapport" (to paste in a message to the team) and opens the logs folder.
"""
import logging
import logging.handlers
import platform
import sys
import threading
import traceback
from datetime import datetime

from . import __version__, paths

MAX_BYTES, BACKUPS = 1_000_000, 3          # customlab.log + customlab.log.1..3: at most ~4 MB on disk
lang = "fr"                                # set by the main window (FR/EN toggle)

TX = {"fr": {"title": "Erreur inattendue", "text": "Une erreur inattendue s'est produite. Votre travail en cours n'a pas forcément été enregistré.\n\nLe détail a été écrit dans le journal :\n{f}\n\nEnvoyez le rapport à l'équipe e-NableLab (bouton « Copier le rapport »).",
             "copy": "Copier le rapport", "open": "Ouvrir le dossier des journaux", "close": "Fermer"},
      "en": {"title": "Unexpected error", "text": "An unexpected error occurred. Your current work may not have been saved.\n\nThe details were written to the log:\n{f}\n\nPlease send the report to the e-NableLab team (\"Copy the report\" button).",
             "copy": "Copy the report", "open": "Open the logs folder", "close": "Close"}}


def log_dir(): return paths.home() / "logs"


def log_file(): return log_dir() / "customlab.log"


def get_logger():
    """The 'customlab' logger, writing to the current <home>/logs/customlab.log (re-targeted if CUSTOMLAB_HOME changed). Never raises."""
    lg = logging.getLogger("customlab"); lg.setLevel(logging.INFO); target = str(log_file())
    for h in list(lg.handlers):
        if getattr(h, "_customlab", False):
            if h.baseFilename == target: return lg
            lg.removeHandler(h); h.close()
    try:
        log_dir().mkdir(parents=True, exist_ok=True)
        h = logging.handlers.RotatingFileHandler(target, maxBytes=MAX_BYTES, backupCount=BACKUPS, encoding="utf-8")
    except OSError: return lg                                   # read-only home: nothing better to do, never crash on logging
    h._customlab = True; h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s")); lg.addHandler(h)
    return lg


def warning(msg):
    try: get_logger().warning(msg)
    except Exception: pass


def report(exc_type, exc, tb):
    """Plain-text report: version, system, time and the full trace."""
    head = f"e-NableLab {__version__} — Python {platform.python_version()} — {platform.platform()} — {datetime.now().isoformat(timespec='seconds')}"
    return head + "\n" + "".join(traceback.format_exception(exc_type, exc, tb))


def show(text):
    """Modal message with the report; only from the GUI thread of a running QApplication."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices, QGuiApplication
    from PySide6.QtWidgets import QApplication, QMessageBox
    if QApplication.instance() is None: return
    t = TX.get(lang, TX["fr"]); box = QMessageBox(QMessageBox.Critical, t["title"], t["text"].format(f=log_file()))
    box.setDetailedText(text); b_copy = box.addButton(t["copy"], QMessageBox.ActionRole); b_open = box.addButton(t["open"], QMessageBox.ActionRole); box.addButton(t["close"], QMessageBox.RejectRole)
    box.exec()
    if box.clickedButton() is b_copy: QGuiApplication.clipboard().setText(text)
    elif box.clickedButton() is b_open: QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_dir())))


_busy = threading.local()


def excepthook(exc_type, exc, tb):
    if issubclass(exc_type, KeyboardInterrupt): return sys.__excepthook__(exc_type, exc, tb)
    if getattr(_busy, "on", False):                             # an error while a report is shown (nested event loop) or being built:
        try: get_logger().error("Exception non gérée (pendant un autre rapport)\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))
        except Exception: pass                                  # log it, but never open a second dialog nor recurse
        return
    _busy.on = True
    try:
        text = report(exc_type, exc, tb)
        try: get_logger().error("Exception non gérée\n%s", text)
        except Exception: pass
        if sys.stderr is not None:                              # None in the windowed (console=False) build
            try: sys.stderr.write(text)
            except Exception: pass
        if threading.current_thread() is threading.main_thread():
            try: show(text)
            except Exception: pass
    finally: _busy.on = False


def _thread_hook(args):
    if args.exc_type is not SystemExit: excepthook(args.exc_type, args.exc_value, args.exc_traceback)


def install():
    """Log every uncaught exception (main and worker threads) and show it to the user (main thread)."""
    sys.excepthook = excepthook; threading.excepthook = _thread_hook
    get_logger().info("Démarrage de e-NableLab %s (%s)", __version__, platform.platform())
