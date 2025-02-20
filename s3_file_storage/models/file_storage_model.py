import uuid

from django.db import models

from s3_file_storage.backends.storages import MultiStorage
from s3_file_storage.constants import StorageProvider, UploadStatus


class FileStorageModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_id = models.UUIDField(default=uuid.uuid4, editable=False)
    file_path = models.FileField(
        max_length=1024, blank=False, null=True, storage=MultiStorage(backend_name="s3")
    )
    file_type = models.CharField(max_length=255, blank=False, null=True)
    description = models.TextField(blank=False, null=True)
    ref_type = models.CharField(max_length=100, blank=True, null=True)
    ref_id = models.CharField(max_length=100, blank=True, null=True)
    file_name = models.CharField(max_length=250, blank=False, null=True)
    original_file_name = models.CharField(max_length=255, blank=False, null=True)
    file_size = models.CharField(max_length=250, blank=False, null=True)
    deleted = models.BooleanField(default=False, blank=True, null=True)
    storage_provider = models.CharField(
        blank=True,
        null=True,
        default=StorageProvider.S3,
        choices=StorageProvider.CHOICES,
    )
    upload_status = models.CharField(
        blank=True,
        null=True,
        default=UploadStatus.PENDING,
        choices=UploadStatus.CHOICES,
    )
    create_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    write_date = models.DateTimeField(auto_now=True, blank=True, null=True)
    create_uid = models.IntegerField(blank=True, null=True, editable=False)
    write_uid = models.IntegerField(blank=True, null=True, editable=False)
    company_id = models.CharField(blank=True, null=True, editable=False)
    
    # Add a class-level attribute for description if needed
    model_description = "File Storage"
    
    class Meta:
        db_table = "file_storage"

    def __str__(self):
        return self.original_file_name or self.file_name
