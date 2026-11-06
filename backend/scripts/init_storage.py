from botocore.exceptions import ClientError

from app.common.storage import S3Storage

storage = S3Storage()
try:
    storage.ready()
except ClientError as exc:
    if exc.response["Error"]["Code"] not in {"404", "NoSuchBucket"}:
        raise
    storage.client.create_bucket(Bucket=storage.bucket)
# No public bucket policy. All browser assets pass through approval-aware API routes.
print("Ayna private asset bucket is ready")
