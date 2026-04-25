"""Convert Northwind Specific SMILE scripts to Generalized versions.

Keyword mapping: Specific -> Generalized
  ADD_PROPERTY     -> ADD PROPERTY
  ADD_PRIMARY_KEY  -> ADD KEY
  ADD_PARTITION_KEY -> ADD PARTITION KEY
  ADD_CLUSTERING_KEY -> ADD CLUSTERING KEY
  ADD_FOREIGN_KEY  -> ADD FOREIGN KEY
  ADD_LABEL        -> ADD LABEL
  DELETE_PROPERTY  -> DELETE PROPERTY
  DELETE_PRIMARY_KEY -> DELETE PRIMARY KEY
  DELETE_PARTITION_KEY -> DELETE PARTITION KEY
  DELETE_CLUSTERING_KEY -> DELETE CLUSTERING KEY
  DELETE_FOREIGN_KEY -> DELETE FOREIGN KEY
  DELETE_ENTITY    -> DELETE ENTITY
  RENAME_PROPERTY  -> RENAME PROPERTY
  RENAME_ENTITY    -> RENAME ENTITY
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
    ('ADD_PROPERTY', 'ADD PROPERTY'),
    ('ADD_FOREIGN_KEY', 'ADD FOREIGN KEY'),
    ('ADD_LABEL', 'ADD LABEL'),
    ('ADD_EMBEDDED', 'ADD EMBEDDED'),
    ('ADD_ENTITY', 'ADD ENTITY'),
    ('DELETE_PARTITION_KEY', 'DELETE PARTITION KEY'),
    ('DELETE_CLUSTERING_KEY', 'DELETE CLUSTERING KEY'),
    ('DELETE_PRIMARY_KEY', 'DELETE PRIMARY KEY'),
    ('DELETE_PROPERTY', 'DELETE PROPERTY'),
    ('DELETE_FOREIGN_KEY', 'DELETE FOREIGN KEY'),
    ('DELETE_ENTITY', 'DELETE ENTITY'),
    ('RENAME_PROPERTY', 'RENAME PROPERTY'),
    ('RENAME_ENTITY', 'RENAME ENTITY'),
    ('CAST_PROPERTY', 'CAST PROPERTY'),
    ('CAST_CONSTRAINT', 'CAST CONSTRAINT'),
    ('COPY_PROPERTY', 'COPY PROPERTY'),
    ('MOVE_PROPERTY', 'MOVE PROPERTY'),
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


def convert_file(smile_path, gen_path):
    """Convert a Specific SMILE file to Generalized version."""
    with open(smile_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    converted = [convert_line(line) for line in lines]

    with open(gen_path, 'w', encoding='utf-8') as f:
        f.writelines(converted)

    basename_in = os.path.basename(smile_path)
    basename_out = os.path.basename(gen_path)
    print(f'  {basename_in} -> {basename_out}')


def main():
    # Find all northwind specific files
    smile_files = sorted(glob.glob(os.path.join(SPECIFIC_DIR, 'northwind_*.smile')))
    print(f'Found {len(smile_files)} Specific files to convert:\n')

    for smile_path in smile_files:
        basename = os.path.basename(smile_path).replace('.smile', '.smile_gen')
        gen_path = os.path.join(GEN_DIR, basename)
        convert_file(smile_path, gen_path)

    print(f'\nDone! {len(smile_files)} Generalized files generated in {GEN_DIR}')


if __name__ == '__main__':
    main()
