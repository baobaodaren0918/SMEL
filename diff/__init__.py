"""SMILE diff package — unified diff engine + the two formatter shapes.

``engine.compute_diff`` is the single source of truth for "how do two Meta
dicts differ". Two formatters convert that diff into the wire shapes the
existing UI / validators expect: ``formatters.to_ui_changes`` for the per-op
Web panel and ``formatters.to_validation_report`` for Layer 1's report.
"""
from diff.engine import compute_diff, DatabaseDiff, EntityDiff, ConstraintDiff
from diff.formatters import to_ui_changes, to_validation_report
