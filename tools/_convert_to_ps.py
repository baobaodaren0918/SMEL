"""Convert Northwind Specific SMEL scripts to Generalized versions.

Keyword mapping: Specific -> Generalized
  ADD_ATTRIBUTE    -> ADD ATTRIBUTE
  ADD_PRIMARY_KEY  -> ADD KEY
  ADD_PARTITION_KEY -> ADD PARTITION KEY
  ADD_CLUSTERING_KEY -> ADD CLUSTERING KEY
  ADD_CONSTRAINT   -> ADD CONSTRAINT
  ADD_RELTYPE      -> ADD RELTYPE
  ADD_LABEL        -> ADD LABEL
  DELETE_ATTRIBUTE -> DELETE ATTRIBUTE
  DELETE_PRIMARY_KEY -> DELETE PRIMARY KEY
  DELETE_PARTITION_KEY -> DELETE PARTITION KEY
  DELETE_CLUSTERING_KEY -> DELETE CLUSTERING KEY
  DELETE_CONSTRAINT -> DELETE CONSTRAINT
  DELETE_RELTYPE   -> DELETE RELTYPE
  DELETE_ENTITY    -> DELETE ENTITY
  RENAME_ATTRIBUTE -> RENAME ATTRIBUTE
  RENAME_ENTITY    -> RENAME ENTITY
  RENAME_RELTYPE   -> RENAME RELTYPE
  NEST             -> NEST
  UNNEST           -> UNNEST
  FLATTEN          -> FLATTEN
  UNFLATTEN        -> UNFLATTEN
  MERGE            -> MERGE
  SPLIT            -> SPLIT
  TRANSFORM        -> TRANSFORM
"""

import os
import glob

SPECIFIC_DIR = os.path.join(os.path.dirname(__file__), 'tests', 'specific')
GEN_DIR = os.path.join(os.path.dirname(__file__), 'tests', 'generalized')

# Keyword replacements (order matters - longer/more specific patterns first)
REPLACEMENTS = [
    ('ADD_PARTITION_KEY', 'ADD PARTITION KEY'),
    ('ADD_CLUSTERING_KEY', 'ADD CLUSTERING KEY'),
    ('ADD_PRIMARY_KEY', 'ADD KEY'),
    ('ADD_ATTRIBUTE', 'ADD ATTRIBUTE'),
    ('ADD_CONSTRAINT', 'ADD CONSTRAINT'),
    ('ADD_RELTYPE', 'ADD RELTYPE'),
    ('ADD_LABEL', 'ADD LABEL'),
    ('ADD_EMBEDDED', 'ADD EMBEDDED'),
    ('ADD_ENTITY', 'ADD ENTITY'),
    ('DELETE_PARTITION_KEY', 'DELETE PARTITION KEY'),
    ('DELETE_CLUSTERING_KEY', 'DELETE CLUSTERING KEY'),
    ('DELETE_PRIMARY_KEY', 'DELETE PRIMARY KEY'),
    ('DELETE_ATTRIBUTE', 'DELETE ATTRIBUTE'),
    ('DELETE_CONSTRAINT', 'DELETE CONSTRAINT'),
    ('DELETE_RELTYPE', 'DELETE RELTYPE'),
    ('DELETE_ENTITY', 'DELETE ENTITY'),
    ('RENAME_ATTRIBUTE', 'RENAME ATTRIBUTE'),
    ('RENAME_ENTITY', 'RENAME ENTITY'),
    ('RENAME_RELTYPE', 'RENAME RELTYPE'),
    ('CAST_ATTRIBUTE', 'CAST ATTRIBUTE'),
    ('CAST_CONSTRAINT', 'CAST CONSTRAINT'),
    ('UNFLATTEN', 'UNFLATTEN'),
    ('UNNEST', 'UNNEST'),
    ('FLATTEN', 'FLATTEN'),
    ('TRANSFORM', 'TRANSFORM'),
    ('MERGE', 'MERGE'),
    ('SPLIT', 'SPLIT'),
    ('NEST', 'NEST'),
]

HEADER_KEYWORDS = ('MIGRATION', 'FROM ', 'USING ')


def convert_line(line):
    """Convert a single line from Specific to Generalized syntax."""
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


def convert_file(smel_path, gen_path):
    """Convert a Specific SMEL file to Generalized version."""
    with open(smel_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    converted = [convert_line(line) for line in lines]

    with open(gen_path, 'w', encoding='utf-8') as f:
        f.writelines(converted)

    basename_in = os.path.basename(smel_path)
    basename_out = os.path.basename(gen_path)
    print(f'  {basename_in} -> {basename_out}')


def main():
    # Find all northwind specific files
    smel_files = sorted(glob.glob(os.path.join(SPECIFIC_DIR, 'northwind_*.smel')))
    print(f'Found {len(smel_files)} Specific files to convert:\n')

    for smel_path in smel_files:
        basename = os.path.basename(smel_path).replace('.smel', '.smel_gen')
        gen_path = os.path.join(GEN_DIR, basename)
        convert_file(smel_path, gen_path)

    print(f'\nDone! {len(smel_files)} Generalized files generated in {GEN_DIR}')


if __name__ == '__main__':
    main()
