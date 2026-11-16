"""Application entry point.

Run from the project root:

    python -m tkinter_app.main
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db import get_db  # noqa: E402
from tkinter_app.app import MainApp  # noqa: E402
from tkinter_app.login import run_login  # noqa: E402


def main() -> None:
    db = get_db()
    while True:
        session = run_login(db)
        if session is None:
            break
        app = MainApp(db, session)
        app.mainloop()
        if not getattr(app, "logout_requested", False):
            break


if __name__ == "__main__":
    main()
