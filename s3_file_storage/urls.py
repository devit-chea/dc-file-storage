from django.urls import include, path
from rest_framework import routers

from s3_file_storage.views.file_storage_view import (
    FileStorageByRefView,
    FileStorageCreateView,
    FileStorageDeleteView,
    FileStoragePreviewView,
    # FileStorageView,
    GenerateDeletePresignedUrlView,
    GenerateDownloadPresignedUrlView,
    GenerateUploadPresignedUrlView,
    UploadFileByPreSignedURLView,
)

router = routers.DefaultRouter(trailing_slash=False)
# router.register(r"file-storage", FileStorageView)

urlpatterns = [  
    # Generate presigned URL
    path(
        "file-storage/generate-upload-presigned-url",
        GenerateUploadPresignedUrlView.as_view(),
        name="file_storage_generate_presigned_url",
    ),
    path(
        "file-storage/generate-download-presigned-url",
        GenerateDownloadPresignedUrlView.as_view(),
        name="file_storage_generate_download_presigned_url",
    ),
    path(
        "file-storage/generate-delete-presigned-url",
        GenerateDeletePresignedUrlView.as_view(),
        name="file-storage_generate_delete_presigned_url",
    ),
    path(
        "file-storage/by-ref",
        FileStorageByRefView.as_view(),
        name="file_storage_by_ref",
    ),
    
    # Preview object
    path(
        "file-storage/preview",
        FileStoragePreviewView.as_view(),
        name="file_storage_preview",
    ),
    path(
        "file-storage/create",
        FileStorageCreateView.as_view(),
        name="file_storage_create",
    ),
    path(
        "file-storage/delete",
        FileStorageDeleteView.as_view(),
        name="file_storage_delete",
    ),
    path(
        "file-storage/put-direct-upload",
        UploadFileByPreSignedURLView.as_view(),
        name="file_storage_connection_upload",
    ),
    
    path("", include(router.urls)),
    
]
