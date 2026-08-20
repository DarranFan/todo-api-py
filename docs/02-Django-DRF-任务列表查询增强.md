# Django DRF 任务列表查询增强

本文承接已经完成 CRUD 的 Todo API，按照顺序增加以下能力：

- 分页
- 客户端调整每页数量
- 按完成状态筛选
- 按标题和描述搜索
- 客户端排序

按照本文步骤操作，可以从已有的基础 Task CRUD API，复现当前阶段的完整代码。

## 1. 开始前的项目状态

项目已经具备：

- Python 3.12
- uv
- Django 5.2
- Django REST Framework
- `Task` 模型
- `TaskSerializer`
- `TaskViewSet`
- `/api/tasks/` CRUD 接口

原来的 `apps/tasks/views.py` 类似：

```python
from rest_framework import viewsets

from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all().order_by("-created_at")
    serializer_class = TaskSerializer
```

## 2. 理解任务列表的请求链路

浏览器请求：

```text
GET /api/tasks/
```

完整链路是：

```text
浏览器或前端
    ↓
config/urls.py 匹配 api/
    ↓
apps/tasks/urls.py 匹配 tasks/
    ↓
TaskViewSet
    ↓
Task.objects 查询数据库
    ↓
TaskSerializer 转换数据
    ↓
返回 JSON
```

`config/urls.py` 负责系统入口：

```python
path("api/", include("apps.tasks.urls"))
```

匹配掉 `api/` 后，将剩余的 `tasks/` 交给 `apps/tasks/urls.py`。

`apps/tasks/urls.py` 中：

```python
router.register("tasks", TaskViewSet)
```

再把请求交给 `TaskViewSet`。

## 3. 理解 `Task.objects`

导入模型：

```python
from .models import Task
```

这里只是导入 `Task` 模型类，没有查询数据库。

几种写法的区别：

```text
Task                  Task 模型类，描述数据结构
Task.objects          操作 Task 数据表的管理器
Task.objects.all()    构建查询所有 Task 的 QuerySet
Task.objects.get(...) 查询一条 Task
Task.objects.filter(...) 按条件查询多条 Task
```

例如：

```python
Task.objects.all()
```

表示查询全部任务。

```python
Task.objects.filter(completed=False)
```

表示查询未完成任务。

`objects` 不只负责查询，也能创建数据：

```python
Task.objects.create(title="学习 Django")
```

## 4. 理解 `serializer_class`

`TaskViewSet` 中：

```python
serializer_class = TaskSerializer
```

左边：

```text
serializer_class
```

是 `ModelViewSet` 约定的配置名称。

右边：

```text
TaskSerializer
```

是我们定义的序列化器类。

这行配置告诉 DRF：

```text
查询时：Task 对象 → TaskSerializer → JSON
创建或修改时：JSON → TaskSerializer 校验 → Task 对象
```

这里传递的是类，而不是提前创建的对象，所以不写括号：

```python
serializer_class = TaskSerializer
```

DRF 在处理请求时会自行创建序列化器实例。

## 5. 配置全局分页

### 作用

如果任务数量很多，一次返回全部数据会增加数据库、服务器和网络压力。分页把数据分成多个小页面。

### 修改 `config/settings.py`

加入：

```python
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),
    "PAGE_SIZE": 10,
}
```

配置含义：

```text
DEFAULT_PAGINATION_CLASS  使用页码分页
PAGE_SIZE                 默认每页 10 条
```

分页请求：

```text
/api/tasks/?page=1
/api/tasks/?page=2
```

DRF 的 `DefaultRouter` 默认生成带尾部斜杠的路径，因此是：

```text
/api/tasks/?page=1
```

而不是：

```text
/api/tasks?page=1
```

`/api/tasks/` 是完整路径，`?page=1` 是查询参数。

### 返回结构变化

分页前：

```json
[
  {"id": 1, "title": "任务一"}
]
```

分页后：

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {"id": 1, "title": "任务一"}
  ]
}
```

字段含义：

```text
count      查询结果总数量
next       下一页 URL
previous   上一页 URL
results    当前页数据
```

### 验证

```bash
uv run python manage.py runserver
```

另一个终端执行：

```bash
curl "http://127.0.0.1:8000/api/tasks/?page=1"
```

## 6. GET 查询参数与 POST 请求体

分页、筛选、搜索、排序是在读取数据，因此通常使用 GET：

```http
GET /api/tasks/?page=2&completed=false
```

前端不必手动拼接字符串。Axios 可以使用：

```javascript
axios.get("/api/tasks/", {
  params: {
    page: 2,
    completed: false,
  },
})
```

常见区分：

```text
GET + params   查询、分页、筛选、搜索、排序
POST + data    创建数据
```

只有查询条件具有复杂嵌套结构、URL 无法合理表达时，才考虑设计专门的 POST 搜索接口。

## 7. 安装筛选依赖

### 作用

使用 `django-filter` 帮助 DRF 根据查询参数筛选 QuerySet。

停止服务器后执行：

```bash
uv add django-filter
```

这会修改：

```text
pyproject.toml
uv.lock
```

## 8. 注册 `django-filter`

### 修改 `config/settings.py`

在 `INSTALLED_APPS` 的第三方应用区域加入：

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "django_filters",

    "apps.tasks.apps.TasksConfig",
]
```

注意：

```text
安装名称    django-filter
注册名称    django_filters
```

这是该第三方包规定的名称。

### 检查

```bash
uv run python manage.py check
```

## 9. 启用精确筛选后端

修改 `config/settings.py` 中的 `REST_FRAMEWORK`：

```python
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),
    "PAGE_SIZE": 10,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
}
```

这里：

```python
"DEFAULT_FILTER_BACKENDS"
```

表示 DRF 列表接口默认使用哪些筛选工具。

## 10. 声明允许筛选的字段

打开 `apps/tasks/views.py`，加入：

```python
filterset_fields = ["completed"]
```

此时：

```python
class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all().order_by("-created_at")
    serializer_class = TaskSerializer
    filterset_fields = ["completed"]
```

`filterset_fields` 是允许筛选字段的白名单。

现在支持：

```text
/api/tasks/?completed=true
/api/tasks/?completed=false
```

大致对应：

```python
Task.objects.filter(completed=True)
Task.objects.filter(completed=False)
```

### 验证

```bash
curl "http://127.0.0.1:8000/api/tasks/?completed=false"
```

筛选与分页可以组合：

```bash
curl "http://127.0.0.1:8000/api/tasks/?completed=false&page=1"
```

分页响应中的 `count` 是筛选后的总数量。

## 11. 启用关键词搜索

DRF 自带 `SearchFilter`，无需安装新依赖。

修改 `config/settings.py`：

```python
"DEFAULT_FILTER_BACKENDS": [
    "django_filters.rest_framework.DjangoFilterBackend",
    "rest_framework.filters.SearchFilter",
],
```

两个后端职责不同：

```text
DjangoFilterBackend  精确筛选，例如 completed=false
SearchFilter         关键词搜索，例如 search=Django
```

## 12. 声明允许搜索的字段

打开 `apps/tasks/views.py`，加入：

```python
search_fields = ["title", "description"]
```

此时：

```python
class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all().order_by("-created_at")
    serializer_class = TaskSerializer
    filterset_fields = ["completed"]
    search_fields = ["title", "description"]
```

请求：

```text
/api/tasks/?search=Django
```

表示在以下字段中搜索关键词：

```text
title 包含 Django
或者
description 包含 Django
```

`search` 是 `SearchFilter` 默认使用的查询参数名，不是模型字段。

可以通过 DRF 配置修改参数名，但当前保留默认名称更简单。

### 验证组合查询

```bash
curl "http://127.0.0.1:8000/api/tasks/?search=Django&completed=false&page=1"
```

URL 中存在 `&` 时应使用引号包裹，避免 Shell 把它解释为后台运行符号。

## 13. 启用客户端排序

修改 `config/settings.py`：

```python
"DEFAULT_FILTER_BACKENDS": [
    "django_filters.rest_framework.DjangoFilterBackend",
    "rest_framework.filters.SearchFilter",
    "rest_framework.filters.OrderingFilter",
],
```

三个后端分别负责：

```text
DjangoFilterBackend  精确筛选
SearchFilter         关键词搜索
OrderingFilter       排序
```

## 14. 声明排序字段与默认排序

修改 `apps/tasks/views.py`：

```python
from rest_framework import viewsets

from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    filterset_fields = ["completed"]
    search_fields = ["title", "description"]
    ordering_fields = ["title", "completed", "created_at", "updated_at"]
    ordering = ["-created_at"]
```

配置区别：

```text
ordering_fields  客户端允许使用的排序字段白名单
ordering         客户端未指定排序时的默认规则
```

原来的：

```python
queryset = Task.objects.all().order_by("-created_at")
```

改为：

```python
queryset = Task.objects.all()
ordering = ["-created_at"]
```

默认排序由排序后端统一负责，职责更加清楚。

### 升序与降序

DRF 使用字段名前的 `-` 表示降序：

```text
?ordering=created_at   升序，对应 ASC
?ordering=-created_at  降序，对应 DESC
```

多字段排序使用逗号：

```text
?ordering=completed,-created_at
```

含义是：

1. 先按 `completed` 升序。
2. 相同时再按 `created_at` 降序。

### 验证

```bash
curl "http://127.0.0.1:8000/api/tasks/?ordering=created_at"
curl "http://127.0.0.1:8000/api/tasks/?ordering=-created_at"
curl "http://127.0.0.1:8000/api/tasks/?ordering=title"
```

完整组合：

```bash
curl "http://127.0.0.1:8000/api/tasks/?completed=false&search=Django&ordering=-created_at&page=1"
```

## 15. 创建可调整每页数量的分页类

### 作用

允许客户端指定 `page_size`，同时通过最大值防止一次请求过多数据。

新建 `apps/tasks/pagination.py`：

```python
from rest_framework.pagination import PageNumberPagination


class TaskPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
```

配置含义：

```text
page_size              默认每页 10 条
page_size_query_param  客户端使用 page_size 参数调整数量
max_page_size          每页最大 100 条
```

例如：

```text
/api/tasks/?page=1&page_size=20
```

即使请求：

```text
/api/tasks/?page_size=10000
```

当前页最多也只会返回 100 条。

## 16. 让 `TaskViewSet` 使用自定义分页

修改 `apps/tasks/views.py`：

```python
from rest_framework import viewsets

from .models import Task
from .pagination import TaskPagination
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    pagination_class = TaskPagination
    filterset_fields = ["completed"]
    search_fields = ["title", "description"]
    ordering_fields = ["title", "completed", "created_at", "updated_at"]
    ordering = ["-created_at"]
```

这里：

```python
pagination_class = TaskPagination
```

表示当前接口使用自定义分页类。

优先级：

```text
视图的 pagination_class
    ↓ 优先
settings.py 的 DEFAULT_PAGINATION_CLASS
```

### 验证

```bash
curl "http://127.0.0.1:8000/api/tasks/?page=1&page_size=2"
curl "http://127.0.0.1:8000/api/tasks/?page=2&page_size=2"
```

## 17. 最终 `REST_FRAMEWORK` 配置

`config/settings.py` 中本阶段相关配置为：

```python
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),
    "PAGE_SIZE": 10,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}
```

虽然 `TaskViewSet` 已指定 `TaskPagination`，全局默认分页仍可供其他未指定专用分页类的接口使用。

## 18. 最终请求处理顺序

一个组合请求：

```text
GET /api/tasks/?completed=false&search=Django&ordering=-created_at&page=1&page_size=10
```

可以理解为：

```text
Task 初始 QuerySet
    ↓
completed 精确筛选
    ↓
search 在 title 和 description 中搜索
    ↓
ordering 排序
    ↓
page 与 page_size 分页
    ↓
TaskSerializer 转换当前页数据
    ↓
返回分页 JSON
```

返回示例：

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 3,
      "title": "学习 Django 分页",
      "description": "完成列表查询功能",
      "completed": false,
      "created_at": "2026-08-13T02:30:00Z",
      "updated_at": "2026-08-13T02:30:00Z"
    }
  ]
}
```

## 19. 关于时间字段

DRF 默认返回 ISO 8601 时间，例如：

```text
2026-08-13T02:30:00Z
```

这种格式适合系统之间传输：

- `T` 分隔日期和时间
- `Z` 表示 UTC
- 前端可以根据用户时区和语言格式化显示

后端默认返回标准时间并没有问题。若必须自定义格式，可以在序列化器分别声明字段：

```python
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class TaskSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(
        format=DATETIME_FORMAT,
        read_only=True,
    )
    updated_at = serializers.DateTimeField(
        format=DATETIME_FORMAT,
        read_only=True,
    )
```

`created_at` 与 `updated_at` 是两个独立字段，所以仍需分别声明；可以复用格式常量，但不应让两个字段共用同一个字段对象。

当前项目建议保留默认 ISO 8601 格式，由未来的前端处理展示样式。

## 20. 检查项目

### 检查 Django 配置

```bash
uv run python manage.py check
```

预期：

```text
System check identified no issues (0 silenced).
```

### 检查是否遗漏模型迁移

```bash
uv run python manage.py makemigrations --check --dry-run
```

预期：

```text
No changes detected
```

本阶段只改变 API 查询行为，没有修改模型，因此不需要生成迁移文件。

## 21. 提交本阶段代码

先查看修改：

```bash
git status
```

本阶段通常修改或新增：

```text
config/settings.py
apps/tasks/views.py
apps/tasks/pagination.py
pyproject.toml
uv.lock
```

提交：

```bash
git add config/settings.py \
  apps/tasks/views.py \
  apps/tasks/pagination.py \
  pyproject.toml \
  uv.lock
```

```bash
git commit -m "feat: add task filtering search ordering and pagination"
git push
```

## 22. 本阶段最终成果

完成本文后，任务列表接口支持：

```text
page        页码
page_size   每页数量，最大 100
completed   完成状态精确筛选
search      标题和描述关键词搜索
ordering    标题、状态、创建时间和更新时间排序
```

完整示例：

```text
/api/tasks/?completed=false&search=Django&ordering=-created_at&page=1&page_size=10
```

本阶段的架构职责划分：

```text
config/settings.py
→ 启用 DRF 全局分页、筛选、搜索和排序能力

apps/tasks/views.py
→ 声明 Task 接口具体允许哪些筛选、搜索和排序字段

apps/tasks/pagination.py
→ 定义 Task 列表的分页规则和安全上限
```
