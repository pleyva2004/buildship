"""Push local /assets (images/videos) -> Nebius Object Storage. Engineer A's twin
of pull_assets.py: one-way mirror up, idempotent (size-compare skip), never
deletes remote objects.

  make assets-push              # upload new/changed files under assets/
  make assets-push DRY=1        # list what would upload

Uses the same .env vars as the pull (NEBIUS_S3_*). Key layout mirrors the local
tree: assets/listings/hero/video/jake_v1/tour.mp4 -> <prefix>listings/hero/video/...
so `make assets-pull` on the other machine reproduces the tree exactly.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root
from agent import config  # side effect: loads .env

ENDPOINT = os.environ.get("NEBIUS_S3_ENDPOINT", "https://storage.eu-north1.nebius.cloud")
BUCKET = os.environ.get("NEBIUS_S3_BUCKET", "")
ACCESS = os.environ.get("NEBIUS_S3_ACCESS_KEY", "")
SECRET = os.environ.get("NEBIUS_S3_SECRET_KEY", "")
PREFIX = os.environ.get("NEBIUS_S3_PREFIX", "assets/")

SKIP = {".gitkeep", ".DS_Store", "index.draft.json"}


def main() -> int:
    if not (BUCKET and ACCESS and SECRET):
        print("Missing NEBIUS_S3_BUCKET / NEBIUS_S3_ACCESS_KEY / NEBIUS_S3_SECRET_KEY in .env")
        return 1
    try:
        import boto3
    except ImportError:
        print("boto3 not installed — run `make deps`")
        return 1

    dry = bool(os.environ.get("DRY"))
    s3 = boto3.client("s3", endpoint_url=ENDPOINT,
                      aws_access_key_id=ACCESS, aws_secret_access_key=SECRET)

    remote = {}
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=PREFIX):
        for obj in page.get("Contents", []):
            remote[obj["Key"]] = obj["Size"]

    pushed = skipped = 0
    for path in sorted(config.ASSETS_DIR.rglob("*")):
        if not path.is_file() or path.name in SKIP:
            continue
        rel = path.relative_to(config.ASSETS_DIR).as_posix()
        key = PREFIX + rel
        if remote.get(key) == path.stat().st_size:
            skipped += 1
            continue
        print(f"{'[dry] would push' if dry else 'push'} assets/{rel} -> {key} ({path.stat().st_size:,}b)")
        if not dry:
            s3.upload_file(str(path), BUCKET, key)
        pushed += 1
    print(f"\n{'would push' if dry else 'pushed'} {pushed}, up-to-date {skipped} "
          f"(bucket: {BUCKET}, prefix: {PREFIX or '—'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
