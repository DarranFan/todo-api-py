from rest_framework import serializers

from .models import Category, Task

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]

    def validate_name(self, value):
        request = self.context["request"]

        queryset = Category.objects.filter(
            owner=request.user,
            name=value,
        )

        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "你已经创建过同名分类。"
            )

        return value

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "completed",
            "category",
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
    def validate_category(self, value):
        request = self.context["request"]

        if value is not None and value.owner_id != request.user.id:
            raise serializers.ValidationError(
                "不能使用其他用户的分类。"
            )

        return value

    def validate_title(self, value):
        if value == "测试":
            raise serializers.ValidationError("不能使用“测试”作为标题。")
        return value

# def validate_title(self, value):
#         title = value.strip()

#         if not title:
#             raise serializers.ValidationError("标题不能为空。")

#         return title
