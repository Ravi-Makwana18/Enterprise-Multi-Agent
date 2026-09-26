import json
import logging
import os
import re
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from backend.config import settings

logger = logging.getLogger(__name__)
_SAFE_KEY = re.compile(r"^[\w\-./]+$")


def _validate_key(key: str) -> str:
    if not _SAFE_KEY.match(key):
        raise ValueError(f"Invalid S3 key: {key!r}")
    return key


def _get_client():
    config = Config(retries={"max_attempts": 3, "mode": "adaptive"})
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        config=config,
    )


def upload_json(key: str, data: Any, bucket: str | None = None) -> str:
    """Upload a JSON-serializable object to S3. Returns the S3 URI."""
    bucket = bucket or settings.s3_bucket_name
    if not bucket:
        raise ValueError("S3_BUCKET_NAME is not configured.")
    full_key = f"{settings.s3_prefix}/{_validate_key(key)}"
    _get_client().put_object(
        Bucket=bucket,
        Key=full_key,
        Body=json.dumps(data, default=str).encode("utf-8"),
        ContentType="application/json",
    )
    return f"s3://{bucket}/{full_key}"


def download_json(key: str, bucket: str | None = None) -> Any:
    """Download and parse a JSON object from S3."""
    bucket = bucket or settings.s3_bucket_name
    if not bucket:
        raise ValueError("S3_BUCKET_NAME is not configured.")
    full_key = f"{settings.s3_prefix}/{_validate_key(key)}"
    try:
        response = _get_client().get_object(Bucket=bucket, Key=full_key)
        return json.loads(response["Body"].read().decode("utf-8"))
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "NoSuchKey":
            return None
        raise


def delete_object(key: str, bucket: str | None = None) -> None:
    bucket = bucket or settings.s3_bucket_name
    if not bucket:
        raise ValueError("S3_BUCKET_NAME is not configured.")
    _get_client().delete_object(Bucket=bucket, Key=f"{settings.s3_prefix}/{_validate_key(key)}")


def generate_presigned_url(key: str, expires_in: int = 3600, bucket: str | None = None) -> str:
    bucket = bucket or settings.s3_bucket_name
    if not bucket:
        raise ValueError("S3_BUCKET_NAME is not configured.")
    return _get_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": f"{settings.s3_prefix}/{_validate_key(key)}"},
        ExpiresIn=expires_in,
    )
