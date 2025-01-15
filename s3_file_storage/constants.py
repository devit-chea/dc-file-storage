class StorageModule:
    GENERIC = "generic"
    
class StorageClassify:
    TEMPS = "temps"
    UPLOADED = "uploaded"

    CHOICES = [
        (TEMPS, "Temp"),
        (UPLOADED, "Uploaded"),
    ]


class StorageProvider:
    LOCAL = "local"
    S3 = "s3"

    CHOICES = [
        (LOCAL, "Local"),
        (S3, "S3"),
    ]
    

class UploadStatus:
    PENDING = "pending"
    COMPLETED = "completed"

    CHOICES = [
        (PENDING, "Pending"),
        (COMPLETED, "Completed"),
    ]
