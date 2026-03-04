"""Convert Northwind Specific SMEL scripts to Pauschalisiert versions.

Keyword mapping: Specific -> Pauschalisiert
  ADD_ATTRIBUTE    -> ADD_PS ATTRIBUTE
  ADD_PRIMARY_KEY  -> ADD_PS KEY
  ADD_PARTITION_KEY -> ADD_PS PARTITION KEY
  ADD_CLUSTERING_KEY -> ADD_PS CLUSTERING KEY
  ADD_CONSTRAINT   -> ADD_PS CONSTRAINT
  ADD_RELTYPE      -> ADD_PS RELTYPE
  ADD_LABEL        -> ADD_PS LABEL
  DELETE_ATTRIBUTE -> DELETE_PS ATTRIBUTE
  DELETE_PRIMARY_KEY -> DELETE_PS PRIMARY KEY
  DELETE_PARTITION_KEY -> DELETE_PS PARTITION KEY
  DELETE_CLUSTERING_KEY -> DELETE_PS CLUSTERING KEY
  DELETE_CONSTRAINT -> DELETE_PS CONSTRAINT
  DELETE_RELTYPE   -> DELETE_PS RELTYPE
  DELETE_ENTITY    -> DELETE_PS ENTITY
  RENAME_ATTRIBUTE -> RENAME_PS ATTRIBUTE
  RENAME_ENTITY    -> RENAME_PS ENTITY
  RENAME_RELTYPE   -> RENAME_PS RELTYPE
  NEST             -> NEST_PS
  UNNEST           -> UNNEST_PS
  FLATTEN          -> FLATTEN_PS
  UNFLATTEN        -> UNFLATTEN_PS
  MERGE            -> MERGE_PS
  SPLIT            -> SPLIT_PS
  TRANSFORM        -> TRANSFORM_PS
"""

import os
import glob

SPECIFIC_DIR = os.path.join(os.path.dirname(__file__), 'tests', 'specific')
PS_DIR = os.path.join(os.path.dirname(__file__), 'tests', 'pauschalisiert')

# Keyword replacements (order matters - longer/more specific patterns first)
REPLACEMENTS = [
    ('ADD_PARTITION_KEY', 'ADD_PS PARTITION KEY'),
    ('ADD_CLUSTERING_KEY', 'ADD_PS CLUSTERING KEY'),
    ('ADD_PRIMARY_KEY', 'ADD_PS KEY'),
    ('ADD_ATTRIBUTE', 'ADD_PS ATTRIBUTE'),
    ('ADD_CONSTRAINT', 'ADD_PS CONSTRAINT'),
    ('ADD_RELTYPE', 'ADD_PS RELTYPE'),
    ('ADD_LABEL', 'ADD_PS LABEL'),
    ('DELETE_PARTITION_KEY', 'DELETE_PS PARTITION KEY'),
    ('DELETE_CLUSTERING_KEY', 'DELETE_PS CLUSTERING KEY'),
    ('DELETE_PRIMARY_KEY', 'DELETE_PS PRIMARY KEY'),
    ('DELETE_ATTRIBUTE', 'DELETE_PS ATTRIBUTE'),
    ('DELETE_CONSTRAINT', 'DELETE_PS CONSTRAINT'),
    ('DELETE_RELTYPE', 'DELETE_PS RELTYPE'),
    ('DELETE_ENTITY', 'DELETE_PS ENTITY'),
    ('RENAME_ATTRIBUTE', 'RENAME_PS ATTRIBUTE'),
    ('RENAME_ENTITY', 'RENAME_PS ENTITY'),
    ('RENAME_RELTYPE', 'RENAME_PS RELTYPE'),
    ('UNFLATTEN', 'UNFLATTEN_PS'),
    ('UNNEST', 'UNNEST_PS'),
    ('FLATTEN', 'FLATTEN_PS'),
    ('TRANSFORM', 'TRANSFORM_PS'),
    ('MERGE', 'MERGE_PS'),
    ('SPLIT', 'SPLIT_PS'),
    ('NEST', 'NEST_PS'),
]

HEADER_KEYWORDS = ('MIGRATION', 'FROM ', 'USING ')


def convert_line(line):
    """Convert a single line from Specific to Pauschalisiert syntax."""
    stripped = line.lstrip()

    # Skip comments, blank lines, and header lines
    if not stripped or stripped.startswith('--'):
        return line
    if any(stripped.startswith(kw) for kw in HEADER_KEYWORDS):
        return line

    # Try each replacement pattern (first match wins)
    for old, new in REPLACEMENTS:
        if stripped.startswith(old):
            return line.replace(old, new, 1)
    return line


def convert_file(smel_path, ps_path):
    """Convert a Specific SMEL file to Pauschalisiert version."""
    with open(smel_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    converted = [convert_line(line) for line in lines]

    with open(ps_path, 'w', encoding='utf-8') as f:
        f.writelines(converted)

    basename_in = os.path.basename(smel_path)
    basename_out = os.path.basename(ps_path)
    print(f'  {basename_in} -> {basename_out}')


def main():
    # Find all northwind specific files
    smel_files = sorted(glob.glob(os.path.join(SPECIFIC_DIR, 'northwind_*.smel')))
    print(f'Found {len(smel_files)} Specific files to convert:\n')

    for smel_path in smel_files:
        basename = os.path.basename(smel_path).replace('.smel', '.smel_ps')
        ps_path = os.path.join(PS_DIR, basename)
        convert_file(smel_path, ps_path)

    print(f'\nDone! {len(smel_files)} Pauschalisiert files generated in {PS_DIR}')


if __name__ == '__main__':
    main()
