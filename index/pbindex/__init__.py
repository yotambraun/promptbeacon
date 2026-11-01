"""The AI Recommendation Index: which open-source projects AI assistants recommend.

A maintainer tool that lives next to PromptBeacon (not in the ``promptbeacon``
package). It runs pinned per-category protocols with PromptBeacon's clients
and cost budget, stores every raw answer and a JSON snapshot, ranks projects
by measured mention rate (with confidence intervals), and renders a static
site. See ``index/README.md``.

Run from the ``index`` directory: ``python -m pbindex --help``.
"""

__version__ = "0.1.0"
