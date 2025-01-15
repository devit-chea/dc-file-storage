from django.conf import settings
from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage


class MultiStorage:
    BACKENDS = {
        "local": FileSystemStorage,
        "s3": S3Boto3Storage,
    }

    def __init__(self, backend_name="s3"):
        backend_class = self.BACKENDS.get(backend_name)
        if not backend_class:
            raise ValueError(f"Unsupported storage backend: {backend_name}")
        self.storage = backend_class()

        # Pass additional parameters for S3
        if backend_name == "s3":
            self.storage = backend_class(
                access_key=settings.S3_ACCESS_KEY_ID,
                secret_key=settings.S3_SECRET_ACCESS_KEY,
                endpoint_url=f"https://{settings.S3_ENDPOINT_URL}",
                bucket_name=settings.S3_STORAGE_BUCKET_NAME,
            )
        else:
            self.storage = backend_class()

    def __getattr__(self, name):
        return getattr(self.storage, name)


class S3MediaStorage(S3Boto3Storage):
    default_acl = "public-read"
    file_overwrite = False

    def __init__(self, *args, **kwargs):
        self.access_key = settings.S3_ACCESS_KEY_ID
        self.secret_key = settings.S3_SECRET_ACCESS_KEY
        self.bucket_name = settings.S3_STORAGE_BUCKET_NAME
        self.endpoint_url = f"https://{settings.S3_ENDPOINT_URL}"

        super().__init__(*args, **kwargs)

