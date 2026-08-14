from rest_framework import serializers

from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "completed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

        extra_kwargs = {
            "title": {
                "error_messages": {
                    "blank": "标题不能为空1。",
                }
            },
        }

    def validate_title(self, value):
        if value == "测试":
            raise serializers.ValidationError("不能使用“测试”作为标题。")
        return value

# def validate_title(self, value):
#         title = value.strip()

#         if not title:
#             raise serializers.ValidationError("标题不能为空。")

#         return title
