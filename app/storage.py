"""Private object storage for PDFs. Local disk is development-only."""
from pathlib import Path
from functools import lru_cache
import boto3
from botocore.exceptions import ClientError
from .config import settings

def _client():
    if not settings.s3_bucket:
        if settings.environment.lower() == "production":
            raise RuntimeError("Private object storage is not configured. Set S3_BUCKET and S3 credentials.")
        return None
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url or None,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )

def save_pdf(key: str, content: bytes) -> None:
    client = _client()
    if client:
        client.put_object(Bucket=settings.s3_bucket, Key=key, Body=content,
                          ContentType="application/pdf")
    else:
        path = Path(settings.private_upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        (path / key).write_bytes(content)

def read_pdf(key: str) -> bytes | None:
    client = _client()
    if client:
        try:
            return client.get_object(Bucket=settings.s3_bucket, Key=key)["Body"].read()
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NotFound"):
                return None
            raise
    path = Path(settings.private_upload_dir) / key
    return path.read_bytes() if path.exists() else None
