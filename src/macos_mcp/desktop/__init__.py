"""Desktop service package.

Deliberately empty, as ``tree`` is. Re-exporting ``Desktop`` here made every
import of a desktop submodule run ``service.py``, which imports the tree,
which reads ``desktop.config`` and ``desktop.views`` -- so reaching the tree
first left the desktop half-initialised and raised ImportError. Import
``Desktop`` from ``macos_mcp.desktop.service``.
"""
