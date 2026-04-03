"""Normal GUI launcher for AutoEditsMusicVideoFor2000s Deluxe.

This module starts the full-featured GUI with a normal entrypoint name.
"""

from autoedit_gui import AutoEditApp


if __name__ == "__main__":
    app = AutoEditApp()
    app.mainloop()
