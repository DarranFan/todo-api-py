# Django DRF 用户认证与数据隔离

本文承接已经完成 Task CRUD、查询增强、自定义业务动作和任务分类的 Todo API，实现多用户认证与数据隔离。

## 这章到底讲什么

原来的 API 没有用户边界：任何客户端都能查看和操作所有 Task 和 Category。

本章实现：

```text
用户使用用户名和密码获取 Token
    ↓
请求携带 Token
    ↓
DRF 识别 request.user
    ↓
创建数据时自动保存 owner
    ↓
查询时只返回 owner 等于当前用户的数据
```

最终效果：

```text
Alice
├── 只能查看和操作自己的 Task
├── 只能查看和操作自己的 Category
└── Task 只能关联自己的 Category

Bob
├── 只能查看和操作自己的 Task
├── 只能查看和操作自己的 Category
└── Task 只能关联自己的 Category
```

一句话概括：

> 本章学习后端如何识别当前用户，并以 owner 为边界隔离不同用户的数据。

## 1. 认证、权限和数据隔离的区别

三个概念分别解决不同问题：

```text
Authentication  当前请求是谁发出的
Permission      当前用户是否允许访问接口
QuerySet        当前用户具体能够访问哪些数据
```

本项目对应：

```text
TokenAuthentication  根据 Token 找到 User
IsAuthenticated      要求用户必须登录
filter(owner=user)   只返回当前用户的数据
```

只配置身份认证还不够。如果 ViewSet 仍然使用：

```python
Task.objects.all()
```

登录用户仍然可能看到所有人的任务。因此，认证和数据查询范围必须一起实现。

## 2. 给 Task 增加 owner

在 `apps/tasks/models.py` 中导入配置：

```python
from django.conf import settings
```

给 Task 增加用户外键：

```python
class Task(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
```

参数含义：

```text
settings.AUTH_USER_MODEL  当前项目使用的用户模型
CASCADE                   删除用户时删除该用户的任务
related_name="tasks"      支持 user.tasks.all() 反向查询
```

数据库实际保存：

```text
Task.owner_id → User.id
```

例如：

```text
User(id=1, username="alice")
    ↑
Task(id=1, owner_id=1, title="学习 Django")
```

常用访问方式：

```python
task.owner
task.owner_id
user.tasks.all()
```

## 3. 给 Category 增加 owner

Category 也需要用户归属，否则 Alice 和 Bob 会共享分类。

```python
class Category(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
    )
```

用户现在拥有两类数据：

```python
user.tasks.all()
user.categories.all()
```

## 4. 分阶段迁移 owner 字段

项目中已经存在 Task 和 Category 时，数据库不知道旧数据应该属于哪个用户。

因此先临时允许 owner 为空：

```python
owner = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    null=True,
    blank=True,
    related_name="tasks",
)
```

生成并执行迁移：

```bash
uv run python manage.py makemigrations tasks
uv run python manage.py migrate
```

本阶段生成：

```text
0003_task_owner.py
0004_category_owner.py
```

查询旧的空 owner 数据：

```bash
uv run python manage.py shell -c \
"from apps.tasks.models import Task, Category; print(Task.objects.filter(owner__isnull=True).count()); print(Category.objects.filter(owner__isnull=True).count())"
```

将旧数据分配给 Alice：

```bash
uv run python manage.py shell -c \
"from django.contrib.auth import get_user_model; from apps.tasks.models import Task, Category; User = get_user_model(); alice = User.objects.get(username='alice'); Task.objects.filter(owner__isnull=True).update(owner=alice); Category.objects.filter(owner__isnull=True).update(owner=alice)"
```

确认空 owner 数量为零后，从模型中删除：

```python
null=True,
blank=True,
```

再次生成迁移时，Django 仍会询问如何处理可能存在的 NULL，因为 `makemigrations` 不检查数据库实际数据。

已经手动处理空数据后，选择：

```text
2) Ignore for now
```

这表示不需要在迁移文件中写一次性默认用户。随后生成并应用：

```text
0005_alter_category_owner_alter_task_owner.py
```

最终数据库要求：

```text
每个 Task 必须有 owner
每个 Category 必须有 owner
```

## 5. 创建本地练习用户

当前项目没有注册 API，所以使用 Django Shell 创建普通用户。

创建 Alice：

```bash
uv run python manage.py shell -c \
"from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_user(username='alice', password='Alice123456!')"
```

创建 Bob：

```bash
uv run python manage.py shell -c \
"from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_user(username='bob', password='Bob123456!')"
```

`create_user()` 会正确处理密码，不能使用普通的 `objects.create()` 代替。

示例密码只用于本地练习，不应用于真实账号。

## 6. 启用 TokenAuthentication

在 `config/settings.py` 的 `INSTALLED_APPS` 中加入：

```python
"rest_framework.authtoken",
```

`authtoken` 提供保存用户 Token 的数据库表。

执行其自带迁移：

```bash
uv run python manage.py migrate
```

这里不需要为 `authtoken` 执行 `makemigrations`，因为第三方包已经提供了迁移文件。

## 7. 配置认证与登录权限

在 `config/settings.py` 中配置：

```python
REST_FRAMEWORK = {
    # 原有分页和筛选配置……
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
```

配置含义：

```text
TokenAuthentication  从请求头读取 Token，并识别 User
IsAuthenticated      没有通过认证的请求不能访问 API
```

未携带 Token 请求：

```bash
curl -i "http://127.0.0.1:8000/api/tasks/"
```

预期：

```http
401 Unauthorized
```

## 8. 添加获取 Token 的接口

修改 `config/urls.py`：

```python
from rest_framework.authtoken.views import obtain_auth_token
```

在 `urlpatterns` 中添加：

```python
path("api/token/", obtain_auth_token),
```

获取 Alice 的 Token：

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/token/" \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"Alice123456!"}'
```

返回：

```json
{
  "token": "实际Token"
}
```

Token 相当于登录凭证，不应写入源码、文档或 Git。

## 9. 携带 Token 请求 API

请求头格式：

```text
Authorization: Token 实际Token
```

注意 `Token` 和实际值之间需要一个空格。

正确示例：

```bash
curl \
  "http://127.0.0.1:8000/api/tasks/" \
  -H "Authorization: Token 这里替换成实际Token"
```

如果遗漏 `Token ` 前缀，DRF 无法识别认证信息，会返回：

```json
{
  "detail": "Authentication credentials were not provided."
}
```

## 10. 创建 Task 时自动设置 owner

在 `TaskViewSet` 中添加：

```python
def perform_create(self, serializer):
    serializer.save(owner=self.request.user)
```

处理过程：

```text
请求携带 Alice Token
    ↓
request.user = Alice
    ↓
perform_create()
    ↓
serializer.save(owner=Alice)
    ↓
数据库保存 owner_id
```

`owner` 没有放进 `TaskSerializer.fields`，所以客户端不能通过请求体伪造任务归属。

## 11. 只查询当前用户的 Task

在 `TaskViewSet` 中添加：

```python
def get_queryset(self):
    return Task.objects.filter(owner=self.request.user)
```

Alice 请求时：

```python
Task.objects.filter(owner=alice)
```

Bob 请求时：

```python
Task.objects.filter(owner=bob)
```

`get_queryset()` 不只保护列表接口，也会影响：

```text
GET     查询单条
PUT     完整修改
PATCH   部分修改
DELETE  删除
POST    complete 自定义动作
```

Alice 访问 Bob 的 Task 时，接口返回 `404 Not Found`。

## 12. 隔离 Category

在 `CategoryViewSet` 中添加：

```python
def get_queryset(self):
    return Category.objects.filter(
        owner=self.request.user
    ).order_by("-created_at")

def perform_create(self, serializer):
    serializer.save(owner=self.request.user)
```

职责：

```text
perform_create()  创建分类时保存当前用户
get_queryset()    只返回当前用户的分类
```

Alice 无法查看、修改或删除 Bob 的 Category。

## 13. 禁止使用其他用户的分类

仅隔离 Category 查询还不够。客户端仍可能直接猜测并提交其他用户的分类 ID。

在 `TaskSerializer` 中添加：

```python
def validate_category(self, value):
    request = self.context["request"]

    if value is not None and value.owner_id != request.user.id:
        raise serializers.ValidationError(
            "不能使用其他用户的分类。"
        )

    return value
```

这里的 `value` 已经是根据客户端分类 ID 查询到的 Category 对象。

校验逻辑：

```text
category=null
→ 允许清除分类

category.owner_id == request.user.id
→ 当前用户自己的分类，允许

category.owner_id != request.user.id
→ 其他用户的分类，返回 400
```

错误响应：

```json
{
  "category": [
    "不能使用其他用户的分类。"
  ]
}
```

## 14. 同一用户分类名称不能重复

业务规则：

```text
Alice + 学习  第一次允许
Alice + 学习  第二次拒绝
Bob   + 学习  允许
```

在 `CategorySerializer` 中添加友好校验：

```python
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
```

更新 Category 时排除当前对象，避免把自己误判为重复数据。

错误响应：

```json
{
  "name": [
    "你已经创建过同名分类。"
  ]
}
```

## 15. 数据库联合唯一约束

Serializer 校验提供友好响应，数据库约束提供最终数据保护。

在 `Category.Meta` 中添加：

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["owner", "name"],
            name="unique_category_name_per_owner",
        )
    ]
```

`fields=["owner", "name"]` 表示两个字段的组合不能重复。

生成并应用：

```text
0006_category_unique_category_name_per_owner.py
```

两层职责：

```text
CategorySerializer.validate_name()
→ 给客户端返回清楚的 400 错误

UniqueConstraint
→ 数据库拒绝重复的 owner + name
```

## 16. 完整验证

Alice 创建分类：

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/categories/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token 这里填写Alice的Token" \
  -d '{"name":"后端学习"}'
```

Alice 再次创建同名分类，预期 `400 Bad Request`。

Bob 创建相同名称，预期成功。

Alice 使用自己的分类创建任务：

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/tasks/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token 这里填写Alice的Token" \
  -d '{"title":"Alice 学习 Django","category":Alice的分类ID}'
```

Alice 使用 Bob 的分类 ID，预期：

```http
400 Bad Request
```

Alice 查询任务列表时，只能看到自己的任务：

```bash
curl \
  "http://127.0.0.1:8000/api/tasks/" \
  -H "Authorization: Token 这里填写Alice的Token"
```

## 17. 最终请求链路

```text
HTTP 请求
    ↓
TokenAuthentication
读取 Authorization 请求头
    ↓
request.user
    ↓
IsAuthenticated
确认用户已经登录
    ↓
ViewSet.get_queryset()
限制为当前用户的数据
    ↓
Serializer
校验输入和关联数据归属
    ↓
ViewSet.perform_create()
自动设置 owner
    ↓
Model 与数据库约束
保存数据并保证完整性
```

## 18. 最终检查

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py showmigrations tasks authtoken
```

当前阶段预期迁移：

```text
[X] 0003_task_owner
[X] 0004_category_owner
[X] 0005_alter_category_owner_alter_task_owner
[X] 0006_category_unique_category_name_per_owner
```

至此，Todo API 已经从公共数据接口升级为具有身份认证、用户归属和数据隔离的多用户 API。
