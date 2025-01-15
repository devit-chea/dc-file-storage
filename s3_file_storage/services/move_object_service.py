from wdg_file_storage.backends.s3 import S3Client

class MoveObjectService:
    
    @staticmethod
    def move_object_keys(
        bucket_name: str, source: str, destination: str, keys_to_copy: list
    ):
        """
        copy object to new folder and delete object from temps

        Args:
            bucket_name (str): define name of bucket we
            source (str): define from source folder
            destination (str): define destination folder
            keys_to_copy (list): the object key list
        """
        bucket = bucket_name
        source_folder = source
        destination_folder = destination

        storage = S3Client()
        storage.copy_objects_and_delete_by_key(
            bucket, source_folder, destination_folder, keys_to_copy
        )
