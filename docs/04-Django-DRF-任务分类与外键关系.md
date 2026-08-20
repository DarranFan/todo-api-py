# Django DRF 任务分类与外键关系

本文承接已经具备 Task CRUD、列表查询增强和 `complete` 自定义动作的 Todo API，实现任务分类功能。

## 这章到底讲什么

这章主要讲 Django 的外键，以及如何在 DRF 接口中真正使用外键。

直白地说，我们原来只有 Task 一张业务表，每个任务之间没有分类。现在增加 Category 表，再让 Task 保存一个分类 ID：

```text
Category
id=1, name="学习"

Task
id=1, title="学习 Django", category_id=1
```

这里的：

```text
Task.id          是任务自己的 ID
Task.category_id 是这个任务关联的分类 ID
```

`category_id=1` 的意思是：这个任务属于 `Category(id=1)`，也就是“学习”分类。

因此，本章不只是学习一行 `ForeignKey` 代码，而是完整实现下面的功能：

```text
创建分类
  ↓
获得分类 ID
  ↓
创建任务时提交分类 ID
  ↓
任务和分类建立关联
  ↓
按分类 ID 查询任务
```

学完本章后，应该能够理解并独立实现：

- 为什么关联数据通常保存 ID，而不是重复保存分类名称
- 如何用 `ForeignKey` 连接两个模型
- 如何通过迁移把模型变化应用到数据库
- 如何让 Serializer 接收和验证关联 ID
- 如何为关联模型提供 CRUD 接口
- 如何根据外键筛选数据

一句话概括：

> 本章以“任务分类”为实际功能，学习如何用外键连接两张表，并把这个关系完整开放成 API。

本阶段完成：

- 创建 `Category` 分类模型
- 建立 Category 与 Task 的一对多关系
- 提供 Category CRUD 接口
- 创建和修改 Task 时关联分类
- 清除 Task 的分类
- 按分类筛选任务

## 1. 功能目标

客户端可以先创建分类：

```http
POST /api/categories/
```

```json
{
  "name": "学习"
}
```

然后创建属于该分类的任务：

```http
POST /api/tasks/
```

```json
{
  "title": "学习 Django",
  "category": 1
}
```

最后按分类查询任务：

```http
GET /api/tasks/?category=1
```

完整功能链路：

```text
创建 Category
    ↓
获得 Category ID
    ↓
创建或修改 Task 时提交 category ID
    ↓
Task.category_id 保存关联
    ↓
根据 category ID 筛选 Task
```

## 2. 数据模型

修改 `apps/tasks/models.py`：

```python
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

`Category` 保存分类名称和创建时间：

```text
id=1, name="学习"
id=2, name="工作"
```

`Task.category` 是指向 Category 的外键。数据库实际保存分类主键：

```text
Task
id=1
title="学习 Django"
category_id=1
```

关系是：

```text
一个 Category 可以关联多个 Task
一个 Task 最多关联一个 Category
```

外键参数的作用：

```text
Category                  指定关联的模型
on_delete=SET_NULL        删除分类时保留任务，将分类设为空
null=True                 数据库允许 category_id 为 NULL
blank=True                API 输入允许不提交分类
related_name="tasks"      支持 category.tasks.all() 反向查询
```

## 3. 数据库迁移

模型变化后执行：

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
```

本阶段生成：

```text
apps/tasks/migrations/0002_category_task_category.py
```

迁移包含两项数据库变化：

```text
创建 Category 表
给 Task 表增加 category_id 外键字段
```

检查模型与迁移是否一致：

```bash
uv run python manage.py makemigrations --check --dry-run
```

预期：

```text
No changes detected
```

## 4. CategorySerializer

在 `apps/tasks/serializers.py` 中导入模型：

```python
from .models import Category, Task
```

创建分类序列化器：

```python
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
```

职责：

```text
客户端 JSON → 校验 → Category 对象
Category 对象 → 转换 → JSON
```

`id` 由数据库生成，`created_at` 由 Django 生成，因此两者只读。客户端创建分类时只需要提交 `name`。

## 5. TaskSerializer 开放 category

在 `TaskSerializer.Meta.fields` 中增加：

```python
fields = [
    "id",
    "title",
    "description",
    "completed",
    "category",
    "created_at",
    "updated_at",
]
```

`ModelSerializer` 默认使用关联对象的主键表示外键，因此 API 接收和返回分类 ID：

```json
{
  "title": "学习 Django",
  "category": 1
}
```

Serializer 会确认 `Category(id=1)` 真实存在，然后创建 Task。

如果分类不存在：

```json
{
  "title": "学习 Django",
  "category": 999
}
```

接口返回 `400 Bad Request`，Task 不会创建。

## 6. CategoryViewSet

在 `apps/tasks/views.py` 中导入：

```python
from .models import Category, Task
from .serializers import CategorySerializer, TaskSerializer
```

添加 ViewSet：

```python
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("-created_at")
    serializer_class = CategorySerializer
```

继承 `ModelViewSet` 后，Category 自动获得标准 CRUD：

```text
GET     查询
POST    创建
PUT     完整修改
PATCH   部分修改
DELETE  删除
```

`ModelViewSet` 创建 Category 的内部过程可简化理解为：

```text
request.data
    ↓
CategorySerializer 校验
    ↓
serializer.save()
    ↓
Category.objects.create(**validated_data)
    ↓
数据库
```

这些通用代码由 DRF 父类实现，项目只需要配置 `queryset` 和 `serializer_class`。

## 7. 注册分类路由

修改 `apps/tasks/urls.py`：

```python
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, TaskViewSet


router = DefaultRouter()
router.register("categories", CategoryViewSet)
router.register("tasks", TaskViewSet)

urlpatterns = router.urls
```

分类接口：

```text
GET     /api/categories/
POST    /api/categories/
GET     /api/categories/{id}/
PUT     /api/categories/{id}/
PATCH   /api/categories/{id}/
DELETE  /api/categories/{id}/
```

系统总路由已经包含：

```python
path("api/", include("apps.tasks.urls"))
```

因此不需要再次修改 `config/urls.py`。

## 8. 创建分类

创建“学习”分类：

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/categories/" \
  -H "Content-Type: application/json" \
  -d '{"name":"学习"}'
```

返回示例：

```json
{
  "id": 1,
  "name": "学习",
  "created_at": "..."
}
```

再创建“工作”分类：

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/categories/" \
  -H "Content-Type: application/json" \
  -d '{"name":"工作"}'
```

查询分类：

```bash
curl "http://127.0.0.1:8000/api/categories/"
```

## 9. 创建带分类的任务

假设“学习”的分类 ID 是 `1`：

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/tasks/" \
  -H "Content-Type: application/json" \
  -d '{"title":"学习 Django","description":"练习任务分类","category":1}'
```

返回示例：

```json
{
  "id": 1,
  "title": "学习 Django",
  "description": "练习任务分类",
  "completed": false,
  "category": 1,
  "created_at": "...",
  "updated_at": "..."
}
```

这里有两个不同的 ID：

```text
id          Task 自己的 ID
category    关联的 Category ID
```

## 10. PUT 和 PATCH 如何使用

PUT 和 PATCH 都用于修改已经存在的数据，但使用方式不同：

```text
PUT     按完整更新的方式提交数据
PATCH   只提交这次需要修改的字段
```

### 10.1 使用 PATCH 修改部分字段

假设数据库中的任务是：

```json
{
  "id": 1,
  "title": "学习 Django",
  "description": "练习任务分类",
  "completed": false,
  "category": 1
}
```

如果只想把任务改为已完成，可以只提交 `completed`：

```bash
curl -X PATCH \
  "http://127.0.0.1:8000/api/tasks/1/" \
  -H "Content-Type: application/json" \
  -d '{"completed":true}'
```

这里：

```text
/api/tasks/1/       表示修改 Task(id=1)
PATCH               表示部分更新
completed=true      是本次唯一要修改的字段
```

没有提交的 `title`、`description` 和 `category` 会保留原值。

修改任务分类也适合使用 PATCH：

```bash
curl -X PATCH \
  "http://127.0.0.1:8000/api/tasks/1/" \
  -H "Content-Type: application/json" \
  -d '{"category":2}'
```

### 10.2 使用 PUT 完整更新

PUT 按完整更新方式执行校验，因此应该提交这条任务需要保留的完整可写内容：

```bash
curl -X PUT \
  "http://127.0.0.1:8000/api/tasks/1/" \
  -H "Content-Type: application/json" \
  -d '{"title":"深入学习 Django","description":"更新学习计划","completed":true,"category":2}'
```

这里一次提交了 Task 的全部可写字段：

```text
title
description
completed
category
```

下面这些字段是只读字段，不需要提交：

```text
id
created_at
updated_at
```

当前项目中 `title` 是必填字段。如果 PUT 时不提交 `title`：

```bash
curl -i -X PUT \
  "http://127.0.0.1:8000/api/tasks/1/" \
  -H "Content-Type: application/json" \
  -d '{"completed":true}'
```

Serializer 会返回 `400 Bad Request`，因为 PUT 没有启用部分更新：

```json
{
  "title": [
    "This field is required."
  ]
}
```

PATCH 则允许省略本次不修改的必填字段：

```text
PUT     partial=False，需要通过完整更新校验
PATCH   partial=True，允许省略本次不修改的字段
```

### 10.3 修改 Category

Category 目前只有一个可写字段 `name`，所以 PUT 和 PATCH 的请求看起来很接近。

使用 PUT 修改分类名称：

```bash
curl -X PUT \
  "http://127.0.0.1:8000/api/categories/1/" \
  -H "Content-Type: application/json" \
  -d '{"name":"编程学习"}'
```

使用 PATCH 修改分类名称：

```bash
curl -X PATCH \
  "http://127.0.0.1:8000/api/categories/1/" \
  -H "Content-Type: application/json" \
  -d '{"name":"编程学习"}'
```

因为 Category 只有 `name` 一个可写字段，两条命令都提交了相同内容。模型字段变多后，两者的区别会更加明显。

实际开发中可以这样选择：

```text
只修改部分字段      使用 PATCH
按完整内容更新对象  使用 PUT
```

## 11. 修改或清除任务分类

假设 Task ID 为 `1`，要改到 Category ID `2`：

```bash
curl -X PATCH \
  "http://127.0.0.1:8000/api/tasks/1/" \
  -H "Content-Type: application/json" \
  -d '{"category":2}'
```

URL 中的 `1` 是 Task ID，请求体中的 `2` 是 Category ID。

清除分类：

```bash
curl -X PATCH \
  "http://127.0.0.1:8000/api/tasks/1/" \
  -H "Content-Type: application/json" \
  -d '{"category":null}'
```

由于外键设置了 `null=True`，任务可以处于未分类状态。

## 12. 按分类筛选任务

修改 `TaskViewSet`：

```python
filterset_fields = ["completed", "category"]
```

按 Category ID 查询：

```bash
curl "http://127.0.0.1:8000/api/tasks/?category=1"
```

它大致对应：

```python
Task.objects.filter(category=1)
```

也可以组合完成状态：

```bash
curl "http://127.0.0.1:8000/api/tasks/?category=1&completed=false"
```

请求处理过程：

```text
GET /api/tasks/?category=1
    ↓
TaskViewSet
    ↓
DjangoFilterBackend
    ↓
Task.objects.filter(category=1)
    ↓
分页
    ↓
TaskSerializer
    ↓
JSON
```

筛选不存在的分类 ID 通常返回空结果，而不是 `404`，因为列表查询成功，只是没有匹配的数据。

## 13. 删除分类后的行为

Task 外键使用：

```python
on_delete=models.SET_NULL
```

删除分类：

```bash
curl -X DELETE \
  "http://127.0.0.1:8000/api/categories/1/"
```

关联的 Task 会保留，其响应中的分类变为：

```json
{
  "category": null
}
```

## 14. 本地练习数据清理

只清除 Task：

```bash
uv run python manage.py shell -c \
"from apps.tasks.models import Task; Task.objects.all().delete()"
```

只重置 SQLite 中的 Task ID：

```bash
uv run python manage.py shell -c \
"from django.db import connection; connection.cursor().execute(\"DELETE FROM sqlite_sequence WHERE name='tasks_task'\")"
```

只清除 Category：

```bash
uv run python manage.py shell -c \
"from apps.tasks.models import Category; Category.objects.all().delete()"
```

只重置 SQLite 中的 Category ID：

```bash
uv run python manage.py shell -c \
"from django.db import connection; connection.cursor().execute(\"DELETE FROM sqlite_sequence WHERE name='tasks_category'\")"
```

重置 ID 是 SQLite 专用的本地练习操作。正式项目不应依赖 ID 连续。

## 15. 最终架构

```text
客户端
  ↓
DefaultRouter
  ├── /api/categories/ → CategoryViewSet
  │                         ↓
  │                    CategorySerializer
  │                         ↓
  │                    Category Model
  │
  └── /api/tasks/      → TaskViewSet
                            ↓
                       TaskSerializer
                            ↓
                       Task Model
                            ↓ ForeignKey
                       Category Model
```

本阶段从单表 CRUD 推进到两个模型协作：

```text
Category 管理分类数据
Task 保存 category_id
Serializer 校验关联 ID
ViewSet 提供接口流程
FilterBackend 提供分类查询
```

## 16. 最终检查

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```

预期：

```text
System check identified no issues (0 silenced).
No changes detected
```

至此，任务分类功能完成。
