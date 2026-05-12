"""SMILE diff package — unified diff engine + the two formatter shapes."""
from diff.engine import compute_diff, DatabaseDiff, EntityDiff, ConstraintDiff
from diff.formatters import to_ui_changes, to_validation_report
