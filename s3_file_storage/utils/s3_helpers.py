import logging

import boto3
from botocore.exceptions import (
    EndpointConnectionError,
    NoCredentialsError,
    PartialCredentialsError,
)
from django.conf import settings

logger = logging.getLogger(__name__)


def get_bucket_name(default_bucket=True):
    """
    Returns the bucket name based on the current tenant or the default bucket name.
    """
    if default_bucket is True:
        return settings.S3_STORAGE_BUCKET_NAME

    return settings.S3_STORAGE_BUCKET_NAME


# For connection testing
def get_s3_client() -> bool:
    """
    Creates and returns a boto3 client for the specified AWS service.

    :param service_name: The name of the AWS service (e.g., 's3', 'dynamodb').
    :param region_name: (Optional) AWS region.
    :param aws_access_key_id: (Optional) AWS access key ID.
    :param aws_secret_access_key: (Optional) AWS secret access key.
    :param aws_session_token: (Optional) AWS session token.
    :return: A boto3 client instance for the specified service.
    """
    try:
        client = boto3.client(
            service_name="s3",
            endpoint_url=f"https://{settings.S3_ENDPOINT_URL}",
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        )
        # Try to list buckets as a health check
        response = client.list_buckets()
        if response["Buckets"]:
            print("S3 Connection Successful: Buckets Found")
            return True
        else:
            print("S3 Connection Successful: No Buckets Found")
            return True

    except NoCredentialsError:
        logger.error("Error: No AWS credentials found.")
    except PartialCredentialsError:
        logger.error("Error: Incomplete AWS credentials.")
    except EndpointConnectionError:
        logger.error("Error: Unable to connect to the S3 endpoint.")
    except Exception as e:
        logger.error(f"Error: {e}")
        return False
