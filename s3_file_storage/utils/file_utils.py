from datetime import datetime
from s3_file_storage.models.file_storage_model import FileStorageModel


class SaveFileMetaService:
    @classmethod
    def create_files_meta_ref_id(
        cls,
        ref_type: str = None,
        ref_id: str = None,
        user_id: str = None,
        company_id=None,
        file_metadata_list: list = [],
    ):
        """
        Bulk creates FileStorageModel instances from a list of file metadata.

        Args:
            file_metadata_list (list): List of dictionaries containing file metadata.
                Example: [{"name": "file1.txt", "file_path": "/path/file1.txt", "size": 1024}, ...]

        Returns:
            list: file_metadata_list
        """
        if not file_metadata_list:
            raise ValueError("File metadata list cannot be empty.")

        # Prepare model instances
        file_instances = [
            FileStorageModel(
                file_id=file.get("file_id"),
                file_path=file.get("file_path"),
                create_uid=user_id,
                ref_id=ref_id,
                ref_type=ref_type,
                company_id=company_id,
                original_file_name=file.get("original_file_name"),
                file_name=file.get("file_name"),
                file=file.get("file_key"),
                file_path=file.get("file_key"),
                file_size=file.get("file_size"),
                file_type=file.get("content_type"),
                description=file.get("description"),
                create_date=datetime.now(),
            )
            # Mapping through file meta data list
            for file in file_metadata_list
        ]

        # Perform bulk create
        created_files = FileStorageModel.objects.bulk_create(file_instances)

        # Convert to JSON-like structure
        created_files_json = [
            {
                "id": file_record.id,
                "original_file_name": file_record.original_file_name,
                "file_name": file_record.file_name,
                "file_size": file_record.file_size,
                "file_type": file_record.file_type,
                "ref_type": file_record.ref_type,
                "ref_id": file_record.ref_id,
                "file": file_record.file.url,
                "file_path": file_record.file_path,
                "file_id": file_record.file_id,
                "description": file_record.description,
                "create_date": file_record.create_date,
                "create_uid": file_record.create_uid,
                "company": file_record.company.id,
            }
            for file_record in created_files
        ]

        return created_files_json


from django.apps import apps
from django.db import transaction
from typing import List, Dict, Optional


class FileManager:
    @classmethod
    def save_files_meta_data(
        cls,
        model_name: str,
        files_meta: List[Dict],
        ref_type: Optional[str] = None,
        ref_id: Optional[int] = None,
    ) -> None:
        """
        Creates or updates file metadata in the specified model.

        :param model_name: The name of the model where the data will be saved (case-insensitive).
        :param files_meta: A list of dictionaries, each containing metadata about a file.
        :param ref_type: Optional reference type to associate with the files.
        :param ref_id: Optional reference ID to associate with the files.
        :raises ValueError: If the model name is invalid or the file metadata is not valid.
        """
        # Get the model class dynamically
        model = apps.get_model("your_app_name", model_name)
        if not model:
            raise ValueError(f"Model '{model_name}' does not exist.")

        # Validate file metadata and model fields
        model_fields = {field.name for field in model._meta.get_fields()}
        for file_meta in files_meta:
            if not isinstance(file_meta, dict):
                raise ValueError("Each file metadata must be a dictionary.")
            if not set(file_meta.keys()).issubset(model_fields):
                raise ValueError(
                    f"Invalid fields in file metadata: {file_meta.keys() - model_fields}"
                )

        # Add ref_type and ref_id to metadata if provided
        if ref_type:
            for file_meta in files_meta:
                file_meta["ref_type"] = ref_type
        if ref_id:
            for file_meta in files_meta:
                file_meta["ref_id"] = ref_id

        # Separate records for update and create
        update_records = []
        new_records = []
        existing_records = {
            record.file_id: record
            for record in model.objects.filter(
                file_id__in=[
                    file["file_id"] for file in files_meta if "file_id" in file
                ]
            )
        }

        for file_meta in files_meta:
            file_id = file_meta.get("file_id")
            if file_id and file_id in existing_records:
                # Update existing record
                for key, value in file_meta.items():
                    setattr(existing_records[file_id], key, value)
                update_records.append(existing_records[file_id])
            else:
                # Prepare new record
                new_records.append(model(**file_meta))

        # Save changes to the database
        with transaction.atomic():
            if update_records:
                model.objects.bulk_update(
                    update_records, fields=list(files_meta[0].keys())
                )
            if new_records:
                model.objects.bulk_create(new_records)
