"""Phase 1.5: deduplicate raw listings.

1. Drop exact job_url duplicates.
2. Drop intra-site duplicates only — the same job re-posted on the SAME board
   is matched by site + normalized company + title + city. The same job posted
   for different cities (e.g. a bank's branches) is kept as separate rows, and
   so is the same job on different boards (it's meaningful per-source data).
"""

import argparse
import re
from pathlib import Path

from crawler.base import read_jsonl, write_jsonl
from pipline.lam_sach import parse_cities


def norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def city_key(location) -> str:
    """Thành phố chuẩn hóa ("Ho Chi Minh City, Vietnam (On-site)" == "…Metropolitan Area");
    thành phố ngoài danh sách ("Khác") thì dùng chính chuỗi địa điểm để không gộp nhầm."""
    cities = parse_cities(location)
    return "/".join(cities) if cities and cities != ["Khác"] else norm(location)


def key_of(row: dict) -> str:
    return f"{row.get('site')}||{norm(row.get('company'))}||{norm(row.get('title'))}||{city_key(row.get('location'))}"


def richer(a: dict, b: dict) -> dict:
    """Prefer the record with a description, else the one with more populated fields."""
    a_desc = len((a.get("description") or "").strip())
    b_desc = len((b.get("description") or "").strip())
    if a_desc and not b_desc:
        return a
    if b_desc and not a_desc:
        return b

    a_fields = sum(1 for v in a.values() if v not in (None, "", []))
    b_fields = sum(1 for v in b.values() if v not in (None, "", []))
    return a if a_fields >= b_fields else b


def main() -> None:
    parser = argparse.ArgumentParser(description="Deduplicate raw listings (Phase 1.5)")
    parser.add_argument("--raw", type=str, default="data/raw")
    parser.add_argument("--out", type=str, default="data/dedup.jsonl")
    args = parser.parse_args()

    rows = []
    for p in sorted(Path(args.raw).glob("*.jsonl")):
        rows.extend(read_jsonl(p))
    print(f"loaded {len(rows)} records", flush=True)

    by_url = {}
    for r in rows:
        url = r.get("job_url")
        if url and url not in by_url:
            by_url[url] = r
    print(f"{len(by_url)} after URL dedup", flush=True)

    by_key = {}
    for r in by_url.values():
        key = key_of(r)
        if key in by_key:
            by_key[key] = richer(by_key[key], r)
        else:
            by_key[key] = r
    print(f"{len(by_key)} after intra-site dedup", flush=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    write_jsonl(out, list(by_key.values()))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()