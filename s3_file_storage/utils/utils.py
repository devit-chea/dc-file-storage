import os
import uuid

from django.core.files.storage import default_storage
from s3_file_storage.backends.storages import S3MediaStorage
from django.core.files.storage import FileSystemStorage
# from django.core.files.storage import get_storage_class
from django.core.files.storage import default_storage


from django.conf import settings

def get_storage_backend(name="default"):
    """
    Get the storage backend dynamically.
    :param name: Name of the storage backend (e.g., "default" or "s3").
    :return: Instance of the storage backend.
    """
    if name not in settings.STORAGES:
        raise ValueError(f"Storage backend '{name}' is not defined in STORAGES.")
    
    storage_config = settings.STORAGES[name]
    # backend_class = get_storage_class(storage_config["BACKEND"])
    backend_class = default_storage
    options = storage_config.get("OPTIONS", {})
    
    return backend_class(**options)

def get_storage(provider=None):
    """
    Returns the appropriate storage backend.
    :param use_s3: Whether to use S3 for storage.
    :return: Storage backend instance.
    """
    if provider == "s3":
        return S3MediaStorage()
    else:
        return FileSystemStorage()


def unique_file_name(filename):
    # Extract file extension
    ext = filename.split(".")[-1]
    # Generate a unique filename using UUID
    unique_name = f"{uuid.uuid4()}.{ext}"
    return unique_name


def unique_file_name_by_original(filename):
    # Extract the file name without extension and make it lowercase
    base_name = os.path.splitext(filename)[0].lower()
    # Replace spaces with underscores
    sanitized_name = base_name.replace(" ", "_")
    # Extract the file extension
    ext = filename.split(".")[-1]
    # Generate a unique filename using UUID
    unique_name = f"{sanitized_name}_{uuid.uuid4()}.{ext}"
    return unique_name

def get_last_part(path:str):
    """
    Extracts the last part of a path after the last '/'.

    Args:
        path (str): The full path as a string.

    Returns:
        str: The last part of the path.
    """
    return path.split('/')[-1]

def get_first_path(path):
    """
    Extracts the first part of a path before the first '/'.

    Args:
        path (str): The full path as a string.

    Returns:
        str: The first part of the path.
    """
    return path.split('/')[0]

def add_slash(path):
    """
    Ensures a string ends with a '/'.
    
    Args:
        path (str): The input string.
    
    Returns:
        str: The string with a trailing '/'.
    """
    return path if path.endswith('/') else path + '/'

def split_first_path(path):
    """
    Splits the path into the first part and the rest after the first '/'.

    Args:
        path (str): The full path as a string.

    Returns:
        tuple: A tuple containing the first part and the remaining path.
    """
    parts = path.split('/', 1)
    first_part = parts[0]
    remaining_path = parts[1] if len(parts) > 1 else ""
    return remaining_path