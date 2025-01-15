import boto3
import logging
from botocore.exceptions import (
    NoCredentialsError,
    ClientError,
    PartialCredentialsError,
    EndpointConnectionError,
)
from django.conf import settings

from s3_file_storage.utils.s3_helpers import get_bucket_name

logger = logging.getLogger(__name__)


class S3Client:
    """
    A wrapper for the boto3 S3 client to abstract and simplify interactions with S3-compatible storage.

    This class initializes a connection to an S3-compatible service using credentials and endpoint
    configurations specified in the Django settings module. It provides a reusable client instance
    for performing operations such as uploading, downloading, and managing files in S3 buckets.

    Attributes:
        client: An instance of the boto3 S3 client configured with the necessary credentials
        and endpoint details.
    """

    def __init__(self):
        self.s3_client_init = "S3 client is not initialized."
        self.client = None  # Initialize client as None
        try:
            self.client = boto3.client(
                service_name="s3",  # Specifies the AWS S3 service.
                endpoint_url=f"https://{settings.S3_ENDPOINT_URL}",  # Custom endpoint for S3-compatible services.
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,  # Access key for authentication.
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,  # Secret key for authentication.
            )
        except (NoCredentialsError, PartialCredentialsError) as e:
            logger.error(f"Credentials error: {e}")
            # Optionally, re-raise or handle the error, e.g., logging, notifying admin
        except EndpointConnectionError as e:
            logger.error(f"Endpoint connection error: {e}")
            # Handle the error if the endpoint is unreachable
        except Exception as e:
            logger.error(f"An error occurred while initializing the S3 client: {e}")
            # Handle other exceptions, such as general network issues

    def upload_file(self, bucket_name, file_name, file_data):
        """
        Upload a file to the S3-compatible storage.
        """
        if self.client is None:
            logger.error(self.s3_client_init)
            return None

        try:
            self.client.put_object(Bucket=bucket_name, Key=file_name, Body=file_data)
            logger.info(f"File {file_name} uploaded successfully to {bucket_name}.")
        except Exception as e:
            logger.error(f"Failed to upload file {file_name}: {e}")

    def generate_upload_presigned_url(
        self,
        file_key: str,
        file_size,
        bucket_name=None,
        content_type=None,
        expiry: int = 3600,
    ):
        """
        Generate a presigned URL for getting or uploading a file from S3.
        :param object_name: The key name for the file in the bucket.
        :return: Presigned upload URL as a string.
        """
        if self.client is None:
            logger.error(self.s3_client_init)
            return None

        try:
            bucket_name = bucket_name or get_bucket_name()

            url = self.client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": bucket_name,
                    "Key": file_key,
                    "ContentLength": file_size,
                    "ContentType": content_type,
                },
                ExpiresIn=expiry,
            )

            return url
        except TypeError as e:
            logger.error(f"Error generating presigned upload URL: {e}")
            raise ValueError("Type error.")
        except ClientError as e:
            logger.error(f"Error generating presigned upload URL: {e}")
            raise ValueError("AWS credentials not configured properly.")

    def generate_download_presigned_url(
        self, file_key: str, bucket_name=None, expiry: int = 3600
    ):
        """
        Generate a presigned URL to download a file from S3.
        :param file_key: Name of the file in the S3 bucket.
        :param expiry: Expiry time in seconds (default: 3600 seconds = 1 hour).
        :return: Presigned download URL as a string.
        """

        if self.client is None:
            logger.error(self.s3_client_init)
            return None

        bucket_name = bucket_name or get_bucket_name()

        try:
            url = self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": bucket_name or settings.S3_STORAGE_BUCKET_NAME,
                    "Key": file_key,
                },
                ExpiresIn=expiry,
            )
        except ClientError as e:
            logger.error(f"Error generating presigned download URL: {e}")
            raise ValueError(f"Error generating presigned URL: {e}")
        return url

    def generate_delete_presigned_url(
        self, file_key: str, bucket_name=None, expiry: int = 3600
    ):
        """
        Generate a presigned URL to delete a file from S3.
        :param file_key: Name of the file in the S3 bucket.
        :param expiry: Expiry time in seconds (default: 3600 seconds = 1 hour).
        :return: Presigned Delete Object URL as a string.
        """

        if self.client is None:
            logger.error(self.s3_client_init)
            return None

        bucket_name = bucket_name or get_bucket_name()

        try:
            url = self.client.generate_presigned_url(
                ClientMethod="delete_object",
                Params={
                    "Bucket": bucket_name or settings.S3_STORAGE_BUCKET_NAME,
                    "Key": file_key,
                },
                ExpiresIn=expiry,
            )
        except ClientError as e:
            logger.error(f"Error generating presigned URL for delete: {e}")
            raise ValueError(f"Error generating presigned URL: {e}")
        return url

    def delete_file_from_bucket(self, file_name: str, bucket_name=None) -> bool:
        """
        Delete file from S3 bucket.
        :param bucket_name: Name of the bucket
        :param file_name: Name of the file
        :return: True if file was deleted, False if not
        """

        if self.client is None:
            logger.error(self.s3_client_init)
            return False

        bucket_name = bucket_name or get_bucket_name()
        try:
            self.client.delete_object(Bucket=bucket_name, Key=file_name)
            return True
        except ClientError as e:
            logger.error(f"Error deleting file from bucket: {e}")
            return False
        except EndpointConnectionError as e:
            logger.error(f"Endpoint connection error: {e}")
            return False

    def check_file_exists_in_bucket(self, bucket_name, file_name) -> bool:
        """
        Check if a file exists in an S3 bucket.
        :param bucket_name: Name of the bucket
        :param file_name: Name of the file
        :return: True if the file exists, False otherwise
        """

        if self.client is None:
            logger.error("S3 client is not initialized.")
            return False

        try:
            self.client.head_object(Bucket=bucket_name, Key=file_name)
            return True
        except ClientError as e:
            # Check for a "Not Found" error code
            if e.response["Error"]["Code"] == "404":
                logger.error(f"Error no bucket: {e}")
                return False
            raise

    def save_file_in_bucket(self, bucket_name, file_name, file_obj):
        """
        Save a file in an S3 bucket.
        :param bucket_name: The name of the bucket
        :param file_name: The name of the file
        :param file_obj: The file object to save
        :raises: Exception if the file already exists
        """

        try:
            self.client.upload_fileobj(file_obj, bucket_name, file_name)
        except ClientError as e:
            logger.error(f"Error generating presigned URL for delete: {e}")
            raise ValueError(f"Failed to upload file: {e}")

    def copy_s3_folder(self, bucket_name, source_folder, destination_folder):
        paginator = self.client.get_paginator("list_objects_v2")

        if self.client is None:
            logger.error(self.s3_client_init)
            return False

        try:
            for page in paginator.paginate(Bucket=bucket_name, Prefix=source_folder):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        source_key = obj["Key"]
                        # Skip copying the "folder" itself if S3 treats it as an object
                        if source_key == source_folder:
                            continue

                        destination_key = source_key.replace(
                            source_folder, destination_folder, 1
                        )
                        copy_source = {"Bucket": bucket_name, "Key": source_key}

                        # Perform the copy
                        self.client.copy_object(
                            Bucket=bucket_name,
                            CopySource=copy_source,
                            Key=destination_key,
                        )

                        # To delete the source file after copying
                        self.client.delete_object(Bucket=bucket_name, Key=source_key)

        except ClientError as e:
            logger.error(f"Error generating presigned URL for delete: {e}")
            raise ValueError(f"Failed to upload file: {e}")

    def copy_objects_and_delete_by_key(
        self,
        bucket_name: str,
        source_folder: str,
        destination_folder: str,
        keys_to_copy: list,
    ):

        if self.client is None:
            logger.error(self.s3_client_init)
            return False

        bucket_name = bucket_name or get_bucket_name()

        try:
            for key in keys_to_copy:
                # Construct the source and destination keys
                source_key = f"{source_folder}{key}"
                destination_key = f"{destination_folder}{key}"

                copy_source = {"Bucket": bucket_name, "Key": source_key}

                # Perform the copy operation
                self.client.copy_object(
                    Bucket=bucket_name, CopySource=copy_source, Key=destination_key
                )
                
                # Perform the delete operation
                self.client.delete_object(Bucket=bucket_name, Key=source_key)

        except ClientError as e:
            logger.error(f"Error generating presigned URL for delete: {e}")
            raise ValueError(f"Failed to upload file: {e}")
