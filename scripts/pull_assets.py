"""Pull rendered assets (images/videos) from Nebius Object Storage -> local /assets.

One-way mirror, idempotent: downloads new/changed objects, skips identical ones
(size match), never deletes local files. The app keeps reading local disk per
the filename contract — the bucket is the A->B transport, NOT a runtime
dependency (CLAUDE.md §2: the stage demo runs on locally cached assets).

  make assets-pull              # mirror bucket -> assets/
  make assets-pull DRY=1        # list what would change, download nothing

Env (.env):
  NEBIUS_S3_ENDPOINT    e.g. https://storage.eu-north1.nebius.cloud
  NEBIUS_S3_BUCKET      bucket name (e.g. vista-assets)
  NEBIUS_S3_ACCESS_KEY / NEBIUS_S3_SECRET_KEY   service-account static keys
  NEBIUS_S3_PREFIX      optional key prefix (default: assets/)
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

# Never let a pull clobber the canonical inventory — index.json is OUR contract
# file (features/traits the app + scorer depend on); renders flow, metadata doesn't.
PROTECTED = {"listings/index.json"}


def main() -> int:
    if not (BUCKET and ACCESS and SECRET):
        print("Missing NEBIUS_S3_BUCKET / NEBIUS_S3_ACCESS_KEY / NEBIUS_S3_SECRET_KEY in .env")
        print("(create static access keys for a service account in the Nebius console,")
        print(" point NEBIUS_S3_ENDPOINT at your region if not eu-north1)")
        return 1
    try:
        import boto3
    except ImportError:
        print("boto3 not installed — run `make deps`")
        return 1

    dry = bool(os.environ.get("DRY"))
    s3 = boto3.client(
        "s3", endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS, aws_secret_access_key=SECRET,
    )

    pulled = skipped = 0
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            rel = key[len(PREFIX):] if key.startswith(PREFIX) else key
            if rel in PROTECTED:
                print(f"skip (protected contract file): {rel}")
                continue
            dest = config.ASSETS_DIR / rel
            if dest.exists() and dest.stat().st_size == obj["Size"]:
                skipped += 1
                continue
            print(f"{'[dry] would pull' if dry else 'pull'} {key} -> assets/{rel} ({obj['Size']:,}b)")
            if not dry:
                dest.parent.mkdir(parents=True, exist_ok=True)
                s3.download_file(BUCKET, key, str(dest))
            pulled += 1
    print(f"\n{'would pull' if dry else 'pulled'} {pulled}, up-to-date {skipped} "
          f"(bucket: {BUCKET}, prefix: {PREFIX or '—'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
