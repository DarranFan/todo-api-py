from rest_framework import status, viewsets

from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Task
from .serializers import CategorySerializer, TaskSerializer
from .pagination import TaskPagination

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("-created_at")
    serializer_class = CategorySerializer

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
    # filterset_fields = ["completed"]
    filterset_fields = ["completed", "category"]
    search_fields = ["title", "description"]
    ordering_fields = ["title", "completed", "created_at", "updated_at"]
    ordering = ["-created_at"]


    # detail=True：针对某一条任务，路径是 POST /tasks/{id}/complete/
    # detail=False 则没有 {id}，会变成 POST /tasks/complete/
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        # request：这次 HTTP 请求（方法、请求头、body、当前用户等），DRF 自动传入
        # 本接口完成任务只靠 URL 里的 id，所以函数体里没用到 request
        # pk：URL 中的任务 id。POST /tasks/3/complete/ 时 pk="3"；没有 id 时默认是 None
        # 按 URL 里的 id 从数据库取出这条任务（实际查找走 get_object，不直接用上面的 pk 参数）
        task = self.get_object()

        # 已经完成过：直接返回 400，后面的保存逻辑不会执行
        if task.completed:
            return Response(
                {"detail": "该任务已经完成，不能重复完成。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 正常路径：标记完成并写入数据库
        task.completed = True
        task.save()

        # 把更新后的 Task 转成 JSON，作为 200 响应返回给前端
        serializer = self.get_serializer(task)
        return Response(serializer.data)
