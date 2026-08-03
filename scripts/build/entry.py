"""Entry point for the frozen build.

PyInstaller needs a module-level script to freeze; the console entry point
declared in pyproject.toml is not one.
"""

from macos_mcp.__main__ import main

if __name__ == "__main__":
    main()
