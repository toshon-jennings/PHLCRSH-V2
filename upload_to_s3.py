"""Upload data files to Cloudflare R2."""

import os
import boto3
from botocore.config import Config

from dotenv import load_dotenv

load_dotenv()
# R2 credentials from environment
ACCOUNT_ID = os.environ["R2_ACCOUNT_ID"]
ACCESS_KEY = os.environ["R2_ACCESS_KEY_ID"]
SECRET_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
BUCKET = os.environ.get("R2_BUCKET", "phlcrsh")

# R2 uses an S3-compatible API at this endpoint
ENDPOINT = f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"

s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)


def upload(local_path: str, key: str | None = None, content_type: str | None = None):
    """Upload a single file. key defaults to the filename."""
    if key is None:
        key = os.path.basename(local_path)

    extra = {}
    if content_type:
        extra["ContentType"] = content_type

    size_mb = os.path.getsize(local_path) / 1e6
    print(f"Uploading {local_path} -> r2://{BUCKET}/{key} ({size_mb:.1f} MB)")

    s3.upload_file(local_path, BUCKET, key, ExtraArgs=extra)
    print(f"  Done.")


if __name__ == "__main__":
    # Files to upload
    uploads = [
        (
            "philly_segments.parquet",
            "data/philly_segments.parquet",
            "application/vnd.apache.parquet",
        ),
    ]

    for local, remote, ctype in uploads:
        if not os.path.exists(local):
            print(f"SKIP: {local} not found")
            continue
        upload(local, remote, ctype)

    print("\nDone. Public URLs (if bucket is public):")
    for _, remote, _ in uploads:
        print(f"  https://pub-<your-hash>.r2.dev/{remote}")
