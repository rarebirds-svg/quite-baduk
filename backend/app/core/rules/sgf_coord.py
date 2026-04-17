"""GTP coordinate <-> (x, y) conversion.

GTP coordinate format: letter (A-T, skipping I) + row number (1=bottom).
Internal format: (x, y) where x=column (0=A), y=row (0=top/row 19 in GTP).

Examples:
  A1  -> (0, 18)   # bottom-left
  A19 -> (0,  0)   # top-left
  T19 -> (18, 0)   # top-right
  Q16 -> (15, 3)   # column Q (0-indexed, skipping I): A=0,B=1,...,H=7,J=8,...,Q=15
"""

COLS = "ABCDEFGHJKLMNOPQRST"  # 19 letters, I omitted
BOARD_SIZE = 19


def gtp_to_xy(coord: str) -> tuple[int, int] | None:
    """Convert GTP coordinate string to (x, y) tuple.

    Returns None for 'pass'. Raises ValueError for invalid input.
    """
    if coord.lower() == "pass":
        return None
    coord = coord.upper()
    if len(coord) < 2:
        raise ValueError(f"Invalid GTP coordinate: {coord!r}")
    col_letter = coord[0]
    if col_letter not in COLS:
        raise ValueError(f"Invalid column letter: {col_letter!r}")
    x = COLS.index(col_letter)
    row_num = int(coord[1:])  # 1-based from bottom
    if not (1 <= row_num <= BOARD_SIZE):
        raise ValueError(f"Row number out of range: {row_num}")
    y = BOARD_SIZE - row_num  # convert to 0-based from top
    return (x, y)


def xy_to_gtp(x: int, y: int) -> str:
    """Convert (x, y) to GTP coordinate string."""
    if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE):
        raise ValueError(f"Coordinates out of range: ({x}, {y})")
    col_letter = COLS[x]
    row_num = BOARD_SIZE - y  # 1-based from bottom
    return f"{col_letter}{row_num}"
