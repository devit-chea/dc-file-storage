from datetime import datetime
import logging
from pathlib import Path
from django.conf import settings
from django.http import FileResponse
from rest_framework import status
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from s3_file_storage.backends.storages import S3MediaStorage
from s3_file_storage.constants import StorageClassify, StorageModule, StorageProvider
from s3_file_storage.models.file_storage_model import FileStorageModel
from s3_file_storage.serializers.file_storage_serializer import (
    DeletePreSignedSerializer,
    DownloadPreSignedSerializer,
    FileStorageCreateValidateSerializer,
    FileStorageSerializer,
    FileStorageValidateByRefSerializer,
    PreSingedUploadSerializer,
)
from s3_file_storage.services.save_file_meta_service import SaveFileMetaService
from s3_file_storage.utils.utils import (
    add_slash,
    get_last_part,
    split_first_path,
    unique_file_name_by_original,
)
from wdg_file_storage.backends.s3 import S3Client
from s3_file_storage.utils.s3_helpers import get_s3_client
import requests
import uuid

logger = logging.getLogger(__name__)


# class FileStorageView(BaseModelViewSet):
#     permission_classes = []  # No Permission

#     model = FileStorageModel
#     queryset = FileStorageModel.objects.all()
#     serializer_class = FileStorageSerializer


class FileStoragePreviewView(APIView):
    permission_classes = []

    def get(self, request, *args, **kwargs):
        file_name = request.data.get("file_name")
        uuid = request.data.get("id")

        if not file_name:
            return Response(
                {"error": "File name not provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            file_instance = FileStorageModel.objects.get(id=uuid, file_name=file_name)

            if not file_instance:
                raise Response(
                    {"error": "File not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            storage = S3MediaStorage()
            
            print(file_instance.file_path)
            
            # Open the file from S3 storage(Base storage config in settings)
            file_obj = storage.open(file_instance.file_path, "rb")

            # Return the file as a response
            return FileResponse(
                file_obj,
                as_attachment=True,
                filename=file_instance.file_name.split("/")[-1],
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve the file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GenerateUploadPresignedUrlView(APIView):
    permission_classes = []
    serializer_class = PreSingedUploadSerializer

    # To be generate presigned URL for upload to s3 direct
    def post(self, request, *args, **kwargs):
        # Validate input using the serializer
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        files_metadata = request.data.get("files", [])
        hr_employee = request.data.get("hr_employee", None)
        ref_type = request.data.get("ref_type", None)
        ref_id = request.data.get("ref_id", None)
        classify = request.data.get("classify", add_slash(StorageClassify.TEMPS))
        module = request.data.get("module", StorageModule.GENERIC)
        expiry = request.data.get("expiry", settings.S3_PRESIGNED_EXPIRE)

        if not files_metadata:
            return Response(
                {"error": "No files metadata provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        presigned_urls = []

        try:
            with transaction.atomic():
                for file_meta in files_metadata:
                    original_file_name = file_meta["original_file_name"]
                    file_size = file_meta["file_size"]
                    content_type = file_meta["content_type"]
                    tenant = 'public'

                    # Generate presigned URL for "put_object"
                    file_name = unique_file_name_by_original(original_file_name)

                    if classify and module:
                        new_obj_key = f"{add_slash(classify)}{add_slash(tenant)}{add_slash(module)}{file_name}"
                    else:
                        new_obj_key = f"{add_slash(StorageClassify.TEMPS)}{add_slash(tenant)}{file_name}"

                    storage = S3Client()
                    presigned_url = storage.generate_upload_presigned_url(
                        file_key=new_obj_key,
                        file_size=file_size,
                        content_type=content_type,
                        expiry=expiry,
                    )

                    # To append file meta
                    presigned_urls.append(
                        {
                            "file_id": uuid.uuid4(),
                            "storage_provider": StorageProvider.S3,
                            "ref_type": ref_type,
                            "ref_id": ref_id,
                            "classify": classify,
                            "module": module,
                            "hr_employee": hr_employee,
                            "original_file_name": original_file_name,
                            "file_name": file_name,
                            "file_key": f"{new_obj_key}",  # as File url
                            "file_size": file_size,
                            "content_type": content_type,
                            "presigned_url": presigned_url,
                        }
                    )

                # Save File meta
                SaveFileMetaService.create_files_meta_ref_id(
                    ref_id=ref_id,
                    ref_type=ref_type,
                    file_metadata_list=presigned_urls,
                )

                return Response({"files": presigned_urls}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Failed to create the file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

# ! Deprecated Soon.
class FileStorageCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FileStorageCreateValidateSerializer

    def post(self, request, *args, **kwargs):
        """Handle saving file info after successful upload."""

        # Validate input using the serializer
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Initialize an array to collect file information
        created_files = []
        object_keys = []

        file_info = request.data.get("file_info", [])
        ref_type = request.data.get("ref_type")
        ref_id = request.data.get("ref_id")
        module = request.data.get("module", StorageModule.GENERIC)

        try:
            with transaction.atomic():
                employee = None
                if "hr_employee" in request.data and request.data["hr_employee"]:
                    employee = Employee.objects.filter(
                        id=request.data["hr_employee"]
                    ).first()
                hr_employee_onbehalf = HrUtil.get_current_employee(
                    self.request.user, self.request.user.base_company
                )

                for file in file_info:
                    original_file_name = file.get("original_file_name", None)
                    file_name = file.get("file_name", None)
                    file_size = file.get("file_size", 0)
                    content_type = file.get("content_type")
                    file_url = file.get("file_key")
                    description = file.get("description")

                    # Re-path object key path
                    remaining_path = split_first_path(file_url)

                    new_file_url = f"{StorageClassify.UPLOADED}/{remaining_path}"

                    object_keys.append(file_name)

                    # Create a record in FileStorageModel
                    file_record = FileStorageModel.objects.create(
                        original_file_name=original_file_name,
                        file_name=file_name,
                        file_size=file_size,
                        file_type=content_type,
                        ref_type=ref_type,
                        ref_id=ref_id,
                        file=new_file_url,
                        description=description,
                        create_date=datetime.now(),
                        create_uid=self.request.user.id,
                        company=self.request.user.base_company,
                        hr_employee_id=employee.id if employee else None,
                        hr_employee_onbehalf_id=(
                            hr_employee_onbehalf.id if hr_employee_onbehalf else None
                        ),
                    )

                    # Append the created file record to the list
                    created_files.append(
                        {
                            "id": file_record.id,
                            "original_file_name": file_record.original_file_name,
                            "file_name": file_record.file_name,
                            "file_size": file_record.file_size,
                            "file_type": file_record.file_type,
                            "ref_type": file_record.ref_type,
                            "ref_id": file_record.ref_id,
                            "file": file_record.file.url,
                            "description": file_record.description,
                            "create_date": file_record.create_date,
                            "create_uid": file_record.create_uid,
                            "company": file_record.company.id,
                            "hr_employee_id": file_record.hr_employee_id,
                            "hr_employee_onbehalf_id": file_record.hr_employee_onbehalf_id,
                        }
                    )

                # copy object to new folder and delete object from temps
                tenant = 'public'
                bucket_name = settings.S3_STORAGE_BUCKET_NAME
                source_folder = f"{StorageClassify.TEMPS}/{tenant}/{module}/"
                destination_folder = f"{StorageClassify.UPLOADED}/{tenant}/{module}/"

                keys_to_copy = object_keys

                storage = S3Client()
                storage.copy_objects_and_delete_by_key(
                    bucket_name, source_folder, destination_folder, keys_to_copy
                )

                return Response(
                    {
                        "message": "File information saved successfully.",
                        "files": created_files,
                    },
                    status=status.HTTP_200_OK,
                )

        except Exception as e:
            return Response(
                {"error": f"Failed to create the file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GenerateDownloadPresignedUrlView(APIView):
    permission_classes = []
    serializer_class = DownloadPreSignedSerializer

    # To be generate presigned URL for download s3 direct
    def post(self, request, *args, **kwargs):
        # Validate input using the serializer
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_key = request.data.get("file_key", None)
        bucket_name = request.data.get("bucket_name", settings.S3_STORAGE_BUCKET_NAME)
        expiry = request.data.get("expiry", settings.S3_PRESIGNED_EXPIRE)

        storage = S3Client()
        download_presigned_url = storage.generate_download_presigned_url(
            file_key=file_key, bucket_name=bucket_name, expiry=expiry
        )

        presigned_url = {
            "file_key": file_key,
            "bucket_name": bucket_name,
            "presigned_url": download_presigned_url,
        }

        return Response(presigned_url, status=status.HTTP_200_OK)


class GenerateDeletePresignedUrlView(APIView):
    permission_classes = []
    serializer_class = DeletePreSignedSerializer

    # To be generate presigned URL for delete s3 direct
    def post(self, request):
        # Validate input using the serializer
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_key = request.data.get("file_key", None)
        bucket_name = request.data.get("bucket_name", None)

        if not file_key and bucket_name:
            return Response(
                {"error": "No file key provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        storage = S3Client()
        download_presigned_url = storage.generate_delete_presigned_url(
            file_key=file_key
        )

        presigned_url = {
            "file_key": file_key,
            "bucket_name": bucket_name,
            "presigned_url": download_presigned_url,
        }

        return Response(presigned_url, status=status.HTTP_200_OK)


class FileStorageByRefView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FileStorageValidateByRefSerializer

    def get(self, request):
        try:
            # Validate input using query parameters
            serializer = self.serializer_class(data=request.query_params)
            serializer.is_valid(raise_exception=True)

            ref_type = request.query_params.get("ref_type", None)
            ref_id = request.query_params.get("ref_id", None)

            # Filter data based on query parameters
            data = FileStorageModel.objects.filter(
                ref_type=ref_type,
                ref_id=ref_id,
                deleted=False,
            ).all()

            serializer_file = FileStorageSerializer(data, many=True)
            return Response(serializer_file.data, status=status.HTTP_200_OK)

        except FileStorageModel.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)


class FileStorageDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        uuid = request.data.get("id", None)
        file_path = request.data.get("file_path", None)

        if not file_path:
            return Response(
                {"message": "File Key is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Fetch the file object from the database
            file_object = FileStorageModel.objects.get(id=uuid, file=file_path)

            storage = S3Client()
            # Delete the file from the S3 bucket
            is_deleted = storage.delete_file_from_bucket(
                file_name=file_object.file.name
            )

            if is_deleted:
                # Delete the file record from the database
                file_object.delete()

                return Response(
                    {"message": "File deleted successfully"}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"message": "Failed to delete the file"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        except Exception as e:
            return Response(
                {"message": f"Failed to delete file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UploadFileByPreSignedURLView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        file_key = request.data.get("file_key")
        file_size = request.data.get("file_size")
        content_type = request.data.get("content_type")
        file_url = request.data.get("file_path")
        pre_signed_url = request.data.get("pre_signed_url")
        module = request.data.get("module", StorageModule.GENERIC)

        file_path = f"{Path(__file__).resolve().parent}/{file_url}"

        if not file_key and file_url:
            return Response(
                {"error": "File key is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            storage = S3Client()
            if pre_signed_url:
                presigned_url = pre_signed_url
            else:
                presigned_url = storage.generate_upload_presigned_url(
                    file_key=file_key,
                    file_size=file_size,
                    content_type=content_type,
                )

            with open(file_path, "rb") as file_data:
                response = requests.put(
                    str(presigned_url),
                    data=file_data,
                    headers={"Content-Type": content_type},
                )

                if response.status_code == 200:
                    logger.error("File uploaded successfully.")

                    bucket_name = settings.S3_STORAGE_BUCKET_NAME
                    source_folder = f"temps/public/{module}/"
                    destination_folder = f"uploaded/public/{module}/"

                    keys_to_copy = [get_last_part(file_key)]

                    storage.copy_objects_and_delete_by_key(
                        bucket_name, source_folder, destination_folder, keys_to_copy
                    )

                else:
                    logger.error(
                        f"Failed to upload file. HTTP {response.status_code}: {response.text}"
                    )

            return Response({"url": presigned_url}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

