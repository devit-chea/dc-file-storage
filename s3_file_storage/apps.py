from django.apps import AppConfig


class FileStorageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 's3_file_storage'
