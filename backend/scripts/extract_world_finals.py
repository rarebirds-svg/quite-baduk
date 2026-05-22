# 빅6 세계기전 결승 SGF를 CWI 아카이브에서 추출해 시드 디렉터리로 복사한다.
"""세계 기전 결승 추출 스크립트.

Usage (from backend/):

    python -m scripts.extract_world_finals /path/to/cwi/games

인자는 CWI 아카이브(homepages.cwi.nl/~aeb/go/games/games.tgz)를 푼
'games/' 디렉터리. 빅6 기전의 결승 대국만 골라
data/pro_games/world_finals/ 로 복사한다 — 기전별 식별 규칙은 아래.

- Fujitsu: 최상위 index.html 의 <h2>Finals</h2> 표 SGF 링크
- Samsung/LG/Chunlan/Toyota: edition 디렉터리의 F1.sgf, F2.sgf … 파일
- Ing: SGF RO[] 값이 'Final N' 패턴

추출 SGF 는 정제 없이 원본 그대로 복사한다 — 정제·메타 추출은
seed_pro_games.py 의 parse_pro_sgf 가 적재 시점에 수행한다.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
OUT_DIR = REPO / "backend" / "data" / "pro_games" / "world_finals"

F_FILE_TOURNAMENTS = ("Samsung", "LG", "Chunlan", "Toyota")
_RO_RE = re.compile(r"RO\[([^\]]*)\]")
_FINAL_RO_RE = re.compile(r"final ?\d*", re.IGNORECASE)


def _fujitsu_finals(games: Path) -> list[Path]:
    """후지쯔: 최상위 index.html 의 Finals 표에서 SGF 링크를 읽는다."""
    idx = (games / "Fujitsu" / "index.html").read_text(encoding="latin-1")
    m = re.search(r"<h2>\s*Finals.*?(?=<h2|</body)", idx, re.S | re.I)
    if not m:
        return []
    rels = re.findall(r'href="(\d+/[^"]+\.sgf)"', m.group(0))
    return [games / "Fujitsu" / r for r in rels]


def _f_file_finals(games: Path, tournament: str) -> list[Path]:
    """삼성·LG·춘란·도요타: edition 디렉터리의 F<숫자>.sgf 결승국."""
    out: list[Path] = []
    for ed in sorted((games / tournament).iterdir()):
        if ed.is_dir():
            out.extend(
                p for p in sorted(ed.glob("*.sgf"))
                if re.fullmatch(r"F\d+", p.stem)
            )
    return out


def _ing_finals(games: Path) -> list[Path]:
    """잉씨배: RO[] 값이 'Final N' 패턴인 SGF."""
    out: list[Path] = []
    for sgf in sorted((games / "Ing").glob("*/*.sgf")):
        txt = sgf.read_text(encoding="latin-1", errors="replace")
        m = _RO_RE.search(txt)
        if m and _FINAL_RO_RE.fullmatch(m.group(1).replace("\r", "").strip()):
            out.append(sgf)
    return out


def _dest_name(games: Path, src: Path) -> str:
    """games/Fujitsu/01/15.sgf -> fujitsu_01_15.sgf"""
    tournament, edition = src.relative_to(games).parts[:2]
    return f"{tournament.lower()}_{edition}_{src.stem}.sgf"


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python -m scripts.extract_world_finals <cwi games dir>")
    games = Path(sys.argv[1]).resolve()
    if not games.is_dir():
        sys.exit(f"not a directory: {games}")

    selected: list[Path] = _fujitsu_finals(games) + _ing_finals(games)
    for t in F_FILE_TOURNAMENTS:
        selected += _f_file_finals(games, t)

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    copied = 0
    missing = 0
    for src in selected:
        if not src.is_file():
            missing += 1
            print(f"  missing: {src}")
            continue
        shutil.copyfile(src, OUT_DIR / _dest_name(games, src))
        copied += 1

    print(f"copied {copied} final SGF -> {OUT_DIR} ({missing} missing)")


if __name__ == "__main__":
    main()
