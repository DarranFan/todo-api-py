# Django DRF Serializer 校验与自定义业务动作

本文承接已经完成 CRUD、分页、筛选、搜索和排序的 Todo API，记录本阶段学习和实现的两个主题：

- 使用 Serializer 编写 Task 标题业务校验
- 使用 ViewSet 自定义 `complete` 业务动作

完成本阶段后，API 不仅能对 Task 进行通用的增删改查，还能通过专用接口表达“完成任务”这一业务行为。

## 1. 本阶段开始前的架构

已有请求链路：

```text
客户端
  ↓
Router
  ↓
TaskViewSet
  ↓
TaskSerializer
  ↓
Task Model
  ↓
SQLite
```

`ModelViewSet` 已经提供标准 CRUD：

```text
GET     /api/tasks/       查询任务列表
POST    /api/tasks/       创建任务
GET     /api/tasks/1/     查询一条任务
PUT     /api/tasks/1/     完整更新任务
PATCH   /api/tasks/1/     部分更新任务
DELETE  /api/tasks/1/     删除任务
```

本阶段在这套架构上增加输入业务校验和标准 CRUD 之外的业务动作。

## 2. Serializer 的职责

Serializer 位于客户端输入和 Model 之间：

```text
客户端 JSON
  ↓
Serializer 转换与校验
  ↓
validated_data
  ↓
Model
```

适合放在 Serializer 中的规则包括：

- 标题是否为空
- 标题是否超过最大长度
- 客户端提交的数据类型是否正确
- 标题是否违反项目特有的业务规则

Serializer 不负责分页、搜索、查询范围和访问权限。这些功能分别由分页类、筛选后端、ViewSet 和权限类负责。

## 3. 字段基础校验与业务校验

`Task` 模型中的标题字段是：

```python
title = models.CharField(max_length=200)
```

`ModelSerializer` 会根据模型自动获得通用规则，例如标题不能为空、不能超过 200 个字符。

当前项目通过 `extra_kwargs` 自定义空标题的错误提示：

```python
extra_kwargs = {
    "title": {
        "error_messages": {
            "blank": "标题不能为空1。",
        }
    },
}
```

提示中的 `1` 只是响应文字的一部分，不会改变校验规则。

项目特有的规则则使用 `validate_字段名()`。当前规则是禁止标题等于“测试”：

```python
def validate_title(self, value):
    if value == "测试":
        raise serializers.ValidationError(
            "不能使用“测试”作为标题。"
        )
    return value
```

这里：

```text
value        经过字段基础处理后的 title 值
raise        数据不合法，立即终止校验并报告错误
return       数据合法，将最终值交给后续流程
```

`validate_title` 遵循 DRF 的方法命名约定，因此 DRF 会自动调用它，并将错误归到 `title` 字段：

```json
{
  "title": [
    "不能使用“测试”作为标题。"
  ]
}
```

## 4. PATCH 部分更新

`ModelViewSet` 自动提供 PATCH：

```http
PATCH /api/tasks/1/
Content-Type: application/json

{
  "completed": true
}
```

PATCH 表示只修改客户端提交的字段。DRF 内部会让 Serializer 使用 `partial=True`，因此没有提交的 `title` 和 `description` 会保留原值。

PATCH 描述的是字段变化：

```text
把 completed 修改为 true
```

它已经能够完成任务，但没有直接表达“执行完成任务这个业务动作”。

## 5. 为什么增加 complete 业务动作

本阶段增加专用接口：

```http
POST /api/tasks/1/complete/
```

两种设计表达的含义不同：

```text
PATCH /api/tasks/1/
客户端决定修改哪些字段

POST /api/tasks/1/complete/
客户端请求后端执行“完成任务”业务动作
```

当前完成动作只是将 `completed` 改为 `True`，但将它设计为业务接口后，可以在后端集中增加规则，例如：

- 禁止重复完成
- 记录完成时间
- 记录操作者
- 写入操作日志
- 触发通知

## 6. 使用 action 增加自定义路由

在 `apps/tasks/views.py` 中导入：

```python
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
```

在 `TaskViewSet` 中添加：

```python
@action(detail=True, methods=["post"])
def complete(self, request, pk=None):
    task = self.get_object()

    if task.completed:
        return Response(
            {"detail": "该任务已经完成，不能重复完成。"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    task.completed = True
    task.save()

    serializer = self.get_serializer(task)
    return Response(serializer.data)
```

关键配置：

```text
@action             声明标准 CRUD 之外的 ViewSet 动作
detail=True         操作一条具体任务，URL 中包含任务 ID
methods=["post"]    只接受 POST 请求
complete            默认成为 URL 的最后一段 complete/
```

项目已经通过 `DefaultRouter` 注册 `TaskViewSet`：

```python
router.register("tasks", TaskViewSet)
```

Router 会自动发现 `@action`，所以不需要在 `urls.py` 中手动增加 `path()`。

## 7. complete 方法的执行过程

收到请求：

```text
POST /api/tasks/1/complete/
```

完整流程：

```text
Router 匹配 task-complete 路由
  ↓
调用 TaskViewSet.complete()
  ↓
self.get_object() 查找 URL 指定的 Task
  ↓
检查任务是否已经完成
  ↓
将 completed 设置为 True
  ↓
task.save() 保存到数据库
  ↓
TaskSerializer 转换更新后的对象
  ↓
Response 返回 JSON
```

`self.get_object()` 会使用当前 ViewSet 的 QuerySet 查找任务。任务不存在时，DRF 自动返回 `404 Not Found`。

## 8. 阻止重复完成

业务规则：

```python
if task.completed:
```

如果任务已经完成，立即返回：

```python
return Response(
    {"detail": "该任务已经完成，不能重复完成。"},
    status=status.HTTP_400_BAD_REQUEST,
)
```

由于执行了 `return`，后面的修改和保存代码不会运行。

两次请求的结果：

```text
第一次：completed=False → 完成任务 → 200 OK
第二次：completed=True  → 拒绝操作 → 400 Bad Request
```

错误使用 `detail`，因为它属于整个业务操作，而不是 Serializer 中某个输入字段。

## 9. HTTP 状态码

本接口涉及的主要状态码：

```text
200 OK              任务成功完成，并返回更新后的任务
400 Bad Request     任务已经完成，不允许重复完成
404 Not Found       URL 指定的任务不存在
```

使用：

```python
status.HTTP_400_BAD_REQUEST
```

比直接写数字 `400` 更容易理解，二者实际表示相同的 HTTP 状态码。

## 10. 创建测试数据

先启动服务器：

```bash
uv run python manage.py runserver
```

在另一个终端创建任务：

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/tasks/" \
  -H "Content-Type: application/json" \
  -d '{"title":"学习 Django 自定义动作","description":"测试 complete 接口","completed":false}'
```

记下响应中的任务 ID。

## 11. 验证完成任务

假设创建的任务 ID 为 1：

```bash
curl -i -X POST \
  "http://127.0.0.1:8000/api/tasks/1/complete/"
```

第一次请求预期返回：

```http
HTTP/1.1 200 OK
```

响应中的 `completed` 应为：

```json
{
  "completed": true
}
```

再次执行相同命令，预期返回：

```http
HTTP/1.1 400 Bad Request
```

```json
{
  "detail": "该任务已经完成，不能重复完成。"
}
```

普通 `curl` 默认只显示响应体。`-i` 会同时显示响应状态和响应头。

只查看状态码也可以使用：

```bash
curl -o /dev/null -s -w "%{http_code}\n" \
  -X POST \
  "http://127.0.0.1:8000/api/tasks/1/complete/"
```

## 12. 本阶段最终架构

```text
DefaultRouter
  ↓
TaskViewSet
  ├── ModelViewSet：标准 CRUD
  └── @action complete：完成任务业务动作
          ↓
     self.get_object()
          ↓
     Task Model
          ↓
     SQLite
```

Serializer 继续负责输入校验和输出转换：

```text
客户端输入
  ↓
TaskSerializer
  ├── 字段基础校验
  └── validate_title() 业务校验
```

ViewSet 负责请求流程和业务动作：

```text
POST /api/tasks/1/complete/
  ↓
TaskViewSet.complete()
  ↓
检查规则、修改模型、返回响应
```

## 13. 本阶段成果

完成本阶段后，项目新增：

- 禁止标题等于“测试”的字段业务校验
- `POST /api/tasks/{id}/complete/` 自定义业务接口
- 完成任务并保存数据库的逻辑
- 阻止任务重复完成的业务规则
- 成功、业务错误和对象不存在三种响应结果

本阶段没有修改 Model，因此不需要生成新的迁移文件。

下一阶段可以学习 `Category` 模型、`ForeignKey` 和一对多数据库关系。
