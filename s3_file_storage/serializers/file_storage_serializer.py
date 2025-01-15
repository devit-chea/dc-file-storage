from rest_framework import serializers

from s3_file_storage.backends.storages import MultiStorage
from s3_file_storage.models.file_storage_model import FileStorageModel


class DownloadPreSignedSerializer(serializers.Serializer):
    file_key = serializers.CharField(max_length=255)

class DeletePreSignedSerializer(serializers.Serializer):
    file_key = serializers.CharField(max_length=255)
    
class FileSerializer(serializers.Serializer):
    original_file_name = serializers.CharField(max_length=255)
    file_size = serializers.IntegerField()
    content_type = serializers.CharField(max_length=50)


class PreSingedUploadSerializer(serializers.Serializer):
    ref_type = serializers.CharField(max_length=50)
    ref_id = serializers.IntegerField(required=False)
    hr_employee = serializers.IntegerField()
    # module = serializers.CharField(max_length=50)
    files = FileSerializer(many=True, required=True)


class FileInfoSerializer(serializers.Serializer):
    original_file_name = serializers.CharField(required=True, allow_blank=False)
    file_size = serializers.IntegerField(required=True)
    content_type = serializers.CharField(required=True)
    file_key = serializers.CharField(required=True)


class FileStorageCreateValidateSerializer(serializers.Serializer):
    file_info = serializers.ListField(child=FileInfoSerializer(), allow_empty=False)


class FileValidationSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        # You can check the file's MIME type here
        if value.content_type not in ["image/jpeg", "image/png"]:
            raise serializers.ValidationError("Invalid file type.")
        return value


class FileStorageValidateByRefSerializer(serializers.Serializer):
    ref_type = serializers.CharField()
    ref_id = serializers.IntegerField(required=False)


class FileUploadValidateSerializer(serializers.Serializer):
    id = serializers.CharField()
    file_path = serializers.CharField()


class FileStorageInfoSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    file_name = serializers.CharField(read_only=True)
    original_file_name = serializers.CharField(read_only=True)
    file_url = serializers.SerializerMethodField()
    image_thumbnail_url = serializers.SerializerMethodField()
    ref_type = serializers.CharField(read_only=True)
    ref_id = serializers.CharField(read_only=True)
    file_size = serializers.CharField(read_only=True)
    deleted = serializers.BooleanField(read_only=True)

    def get_file_url(self, obj):
        try:
            return obj.file.url
        except Exception:
            return None

    def get_image_thumbnail_url(self, obj):
        try:
            return obj.image_thumbnail.url
        except Exception:
            return None


class FileStorageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileStorageModel

        file = serializers.ListField(
            child=serializers.FileField(
                max_length=100000, allow_empty_file=False, use_url=False
            )
        )

        fields = "__all__"

    def create(self, validated_data):
        validated_data["create_uid"] = self.context["user_id"]
        return super().create(validated_data)

    def get_files_info(self, obj):
        file = FileStorageModel.objects.filter(ref_id=obj.id).all()
        data = None

        if file:
            serializer = FileStorageInfoSerializer(file, many=True)
            data = serializer.data
        return data
