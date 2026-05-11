from __future__ import annotations

import asyncio
import uuid

import boto3

from app.config import settings


s3_client = boto3.client(
    "s3",
    region_name=settings.AWS_REGION,
)


async def upload_image_to_s3(
    file_bytes: bytes,
    content_type: str,
    folder: str = "template-assets",
) -> str:
    key = f"{folder}/{uuid.uuid4()}.{content_type.split('/')[-1]}"
    await asyncio.to_thread(
        s3_client.put_object,
        Bucket=settings.AWS_S3_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
        ACL="public-read",
    )
    return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"


async def upload_thumbnail_to_s3(file_bytes: bytes, template_id: str) -> str:
    key = f"thumbnails/{template_id}.png"
    await asyncio.to_thread(
        s3_client.put_object,
        Bucket=settings.AWS_S3_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType="image/png",
        ACL="public-read",
    )
    return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"