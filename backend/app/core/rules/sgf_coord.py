"""GTP coordinate <-> (x, y) conversion.

GTP coordinate format: letter (A-T, skipping I) + row number (1=bottom).
Internal format: (x, y) where x=column (0=A), y=row (0=top).

Examples (size=19):
  A1  -> (0, 18)   # bottom-left
  A19 -> (0,  0)   # top-left
  T19 -> (18, 0)   # top-right
"""

COLS = "ABCDEFGHJKLMNOPQRST"  # 19 letters, I omitted; sliced by `size`


def gtp_to_xy(coord: str, size: int) -> tuple[int, int] | None:
    """Convert GTP coordinate string to (x, y).

    Returns None for 'pass'. Raises ValueError for invalid input or out-of-range.
    """
    if coord.lower() == "pass":
        return None
    coord = coord.upper()
    if len(coord) < 2:
        raise ValueError(f"Invalid GTP coordinate: {coord!r}")
    col_letter = coord[0]
    cols = COLS[:size]
    if col_letter not in cols:
        raise ValueError(f"Invalid column letter: {col_letter!r}")
    x = cols.index(col_letter)
    row_num = int(coord[1:])
    if not (1 <= row_num <= size):
        raise ValueError(f"Row number out of range: {row_num}")
    y = size - row_num
    return (x, y)


def xy_to_gtp(x: int, y: int, size: int) -> str:
    """Convert (x, y) to GTP coordinate string."""
    if not (0 <= x < size and 0 <= y < size):
        raise ValueError(f"Coordinates out of range: ({x}, {y})")
    cols = COLS[:size]
    col_letter = cols[x]
    row_num = size - y
    return f"{col_letter}{row_num}"
