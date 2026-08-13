from rest_framework import viewsets

from .models import Task
from .serializers import TaskSerializer
from .pagination import TaskPagination



# ModelViewSet = 一套现成的接口模板
# 写好下面两行后，会自动生成这些 HTTP 接口：
#   GET    /tasks/       查列表
#   POST   /tasks/       新建一条
#   GET    /tasks/1/     查某一条
#   PUT/PATCH /tasks/1/  改某一条
#   DELETE /tasks/1/     删某一条
class TaskViewSet(viewsets.ModelViewSet):
    # 从数据库取哪些 Task？
    # Task.objects.all() = 全部任务
    # .order_by("-created_at") = 新的在前（减号表示倒序）
    queryset = Task.objects.all()

    # 把“数据库里的 Task”和“接口的 JSON”互相转换，并检查字段是否合法
    # 例如：{"title": "买菜"} <-> Task 对象
    serializer_class = TaskSerializer
    pagination_class = TaskPagination
    filterset_fields = ["completed"]
    search_fields = ["title", "description"]
    ordering_fields = ["title", "completed", "created_at", "updated_at"]
    ordering = ["-created_at"]
