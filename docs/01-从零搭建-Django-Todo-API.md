# 从零搭建 Django Todo API

本文是一份可独立执行的项目搭建手册。按照步骤顺序操作，可以从空目录搭建一个基于 Python 3.12、uv、Django 5.2 和 Django REST Framework 的待办事项 API。

## 1. 明确项目架构

项目采用模块化单体架构：

```text
客户端
  ↓
系统总路由
  ↓
tasks 业务路由
  ↓
ViewSet 请求处理层
  ↓
Serializer 数据转换与校验层
  ↓
Model 数据模型层
  ↓
SQLite 数据库
```

第一版只实现：

- 创建待办事项
- 查询待办事项
- 修改待办事项
- 删除待办事项
- 校验输入数据

暂不实现登录、多用户权限、自动化测试和生产部署。

## 2. 创建项目根目录

### 作用

创建容纳项目配置、代码、虚拟环境和数据库的最外层目录。

### 操作

```bash
mkdir todo-api
cd todo-api
```

确认位置：

```bash
pwd
```

输出路径的结尾应该是 `todo-api`。

## 3. 初始化 Python 项目

### 作用

让当前目录成为由 uv 管理的 Python 项目。

### 操作

```bash
uv init --bare --python 3.12
```

使用 `--bare` 是因为 Django 稍后会生成自己的项目入口，不需要 uv 创建示例 `main.py`。

执行后会产生：

```text
todo-api/
└── pyproject.toml
```

## 4. 严格固定 Python 3.12

### 作用

`>=3.12` 也允许 Python 3.13、3.14 等更高版本。为了让项目严格使用 Python 3.12，需要同时配置允许范围和 uv 的解释器选择。

### 修改 `pyproject.toml`

将：

```toml
requires-python = ">=3.12"
```

改成：

```toml
requires-python = ">=3.12,<3.13"
```

### 固定 uv 使用的版本

```bash
uv python pin 3.12
```

这会创建 `.python-version`，内容通常是：

```text
3.12
```

两份配置的职责不同：

```text
pyproject.toml   声明项目允许的 Python 版本范围
.python-version  告诉 uv 在当前项目具体选择 Python 3.12
```

## 5. 安装项目依赖

### 作用

安装 Web 框架、REST API 框架和环境变量读取工具。

### 操作

```bash
uv add "django>=5.2,<5.3" djangorestframework django-environ
```

uv 会：

- 把依赖写入 `pyproject.toml`
- 把精确版本记录到 `uv.lock`
- 创建项目虚拟环境 `.venv`
- 把依赖安装到 `.venv`

### 验证

```bash
uv run python --version
uv run django-admin --version
```

预期分别看到：

```text
Python 3.12.x
5.2.x
```

## 6. 创建 Django 系统骨架

### 作用

创建 Django 的系统配置包和项目管理入口。

### 操作

```bash
uv run django-admin startproject config .
```

命令含义：

```text
uv run       在项目虚拟环境中执行命令
django-admin Django 管理工具
startproject 创建 Django 系统骨架
config       配置包名称
.            在当前目录生成文件
```

执行后主要结构为：

```text
todo-api/
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── manage.py
```

验证骨架：

```bash
uv run python manage.py check
```

预期输出：

```text
System check identified no issues (0 silenced).
```

## 7. 创建业务模块容器

### 作用

将系统配置与业务代码分开：

```text
config/  系统级配置
apps/    业务模块
```

### 操作

```bash
mkdir apps
touch apps/__init__.py
```

`__init__.py` 让 Python 明确地把 `apps` 识别为包。

## 8. 创建 tasks 业务模块

### 作用

创建负责待办事项业务的 Django app。

### 操作

```bash
mkdir apps/tasks
uv run python manage.py startapp tasks apps/tasks
```

执行后：

```text
apps/tasks/
├── migrations/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── tests.py
└── views.py
```

### 修正应用导入路径

打开 `apps/tasks/apps.py`：

```python
from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tasks"
```

必须使用 `apps.tasks`，因为 `tasks` 实际位于 `apps/` 包中。

## 9. 注册 tasks 和 DRF

### 作用

安装依赖或创建 app 后，Django 不会自动加载它们。需要在系统应用清单中注册。

打开 `config/settings.py`，修改 `INSTALLED_APPS`：

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",

    "apps.tasks.apps.TasksConfig",
]
```

`django-environ` 只是供 `settings.py` 使用的 Python 工具，不是 Django app，不需要加入 `INSTALLED_APPS`。

检查配置：

```bash
uv run python manage.py check
```

## 10. 定义 Task 数据模型

### 作用

模型用 Python 类描述数据库表的结构。

打开 `apps/tasks/models.py`：

```python
from django.db import models


class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

字段说明：

| 字段 | 作用 |
|---|---|
| `title` | 最长 200 个字符的标题 |
| `description` | 可留空的详细说明 |
| `completed` | 是否完成，默认 `False` |
| `created_at` | 创建时自动记录时间 |
| `updated_at` | 每次修改时自动更新时间 |

Django 会自动添加 `id` 主键。

`models.Model` 是 Django 的模型父类。继承它后，`Task` 才能映射为数据库表，并获得 ORM 查询能力。

## 11. 生成并执行数据库迁移

### 作用

`models.py` 只是 Python 中的结构定义。数据库需要通过迁移文件建立真实数据表。

### 生成迁移计划

```bash
uv run python manage.py makemigrations tasks
```

通常会生成：

```text
apps/tasks/migrations/0001_initial.py
```

### 执行迁移

```bash
uv run python manage.py migrate
```

二者区别：

```text
makemigrations  根据模型变化生成迁移计划
migrate         把迁移计划应用到数据库
```

执行后，项目根目录会出现本地 SQLite 数据库：

```text
db.sqlite3
```

## 12. 创建序列化器

### 作用

序列化器负责：

- 将 Task 模型对象转换成 JSON
- 将客户端 JSON 转换成可保存的数据
- 校验客户端输入
- 控制 API 公开哪些字段

新建 `apps/tasks/serializers.py`：

```python
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
                    "blank": "标题不能为空。",
                    "required": "请提供标题。",
                    "max_length": "标题不能超过 200 个字符。",
                }
            }
        }
```

关键配置：

```text
Meta             DRF 约定的内部配置类
model            指定对应的模型
fields           指定 API 接收和返回的字段
read_only_fields 指定只允许读取的字段
extra_kwargs     修改自动生成字段的额外配置
```

空标题属于 DRF 的字段基础校验，因此应通过 `error_messages["blank"]` 修改提示，而不是依赖 `validate_title()`。

如果以后有项目特有的业务规则，可以增加：

```python
def validate_title(self, value):
    if value == "测试":
        raise serializers.ValidationError("不能使用‘测试’作为标题。")
    return value
```

DRF 会按 `validate_字段名` 的命名约定自动调用它。

## 13. 创建 API 请求处理层

### 作用

ViewSet 接收 HTTP 请求，并决定查询什么模型、使用什么序列化器。

打开 `apps/tasks/views.py`：

```python
from rest_framework import viewsets

from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all().order_by("-created_at")
    serializer_class = TaskSerializer
```

`ModelViewSet` 自动提供常见 CRUD 操作：

```text
GET     查询
POST    创建
PUT     完整修改
PATCH   部分修改
DELETE  删除
```

`order_by("-created_at")` 表示按创建时间倒序排列，最新任务排在最前面。

## 14. 创建 tasks 模块路由

### 作用

将 URL 与 `TaskViewSet` 连接起来。

新建 `apps/tasks/urls.py`：

```python
from rest_framework.routers import DefaultRouter

from .views import TaskViewSet


router = DefaultRouter()
router.register("tasks", TaskViewSet)

urlpatterns = router.urls
```

路由器会自动生成：

```text
GET     /tasks/
POST    /tasks/
GET     /tasks/{id}/
PUT     /tasks/{id}/
PATCH   /tasks/{id}/
DELETE  /tasks/{id}/
```

## 15. 接入系统总路由

### 作用

业务模块路由创建后，还要连接到 Django 的系统入口。

打开 `config/urls.py`：

```python
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.tasks.urls")),
]
```

最终 URL 由两部分组合：

```text
系统前缀 api/ + 模块路径 tasks/ = /api/tasks/
```

`api/` 不是 Django 强制要求的名称，而是用于清楚地区分 API 与普通网页、管理后台等入口。

## 16. 使用环境变量管理敏感配置

### 作用

`SECRET_KEY` 是 Django 用来生成和验证安全签名的服务器密钥，不是用户密码或数据库密码。真实密钥不应写入可共享的源码。

### 创建 `.env`

先生成密钥：

```bash
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

在项目根目录创建 `.env`：

```env
DJANGO_SECRET_KEY=这里填写刚才生成的密钥
DJANGO_DEBUG=True
```

不要把真实密钥发送到聊天、日志或公开仓库。

### 修改 `config/settings.py`

文件开头相关部分改为：

```python
from pathlib import Path

import environ


BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")

DEBUG = env("DJANGO_DEBUG")
```

执行顺序是：

```text
确定项目根目录
  ↓
创建环境配置读取器
  ↓
读取项目根目录中的 .env
  ↓
获取 DJANGO_SECRET_KEY 和 DJANGO_DEBUG
```

`DJANGO_DEBUG=(bool, False)` 表示将该配置转换成 Python 布尔值；未配置时默认使用 `False`。

### 检查配置

```bash
uv run python manage.py check
```

## 17. 创建环境配置模板

### 作用

真实 `.env` 不能共享，但其他开发者需要知道项目要求哪些配置项。因此创建可提交的空白模板 `.env.example`。

项目根目录新建 `.env.example`：

```env
DJANGO_SECRET_KEY=replace-with-your-secret-key
DJANGO_DEBUG=True
```

二者区别：

```text
.env          真实配置，不提交 Git
.env.example  配置清单和格式，可以提交 Git
```

其他开发者拉取代码后执行：

```bash
cp .env.example .env
```

然后生成自己的密钥并填写到 `.env`。

## 18. 创建 `.gitignore`

### 作用

避免把虚拟环境、缓存、本地数据库和真实密钥提交到 Git。

项目根目录创建 `.gitignore`：

```gitignore
# Python 缓存
__pycache__/
*.py[cod]

# 虚拟环境
.venv/

# 本地数据库
db.sqlite3

# 真实环境配置
.env

# macOS
.DS_Store
```

以下文件不应忽略：

```text
uv.lock          锁定应用项目的精确依赖版本
.python-version  指明项目使用 Python 3.12
.env.example     告诉其他开发者需要哪些配置
migrations/      记录数据库结构变化
```

## 19. 创建精简 README

项目根目录创建 `README.md`：

````markdown
# Todo API

使用 Python 3.12、Django 5.2 和 Django REST Framework 构建的待办事项 API。

## 技术栈

- Python 3.12
- uv
- Django 5.2
- Django REST Framework
- SQLite

## 安装依赖

```bash
uv sync
```

## 配置环境

```bash
cp .env.example .env
```

生成 Django 密钥：

```bash
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

将生成的密钥填写到 `.env`：

```env
DJANGO_SECRET_KEY=这里填写生成的密钥
DJANGO_DEBUG=True
```

## 初始化数据库

```bash
uv run python manage.py migrate
```

## 启动项目

```bash
uv run python manage.py runserver
```

API 地址：

```text
http://127.0.0.1:8000/api/tasks/
```

## 检查项目

```bash
uv run python manage.py check
```
````

README 负责说明如何运行已经搭建好的项目；本文档负责说明如何从零搭建项目。

## 20. 初始化 Git 仓库

### 作用

让 Git 开始记录项目文件和后续修改历史。

```bash
git init
git status
```

`git init` 只创建本地 `.git/` 仓库，不会自动提交，也不会上传到 GitHub。

在首次提交前，应确认 `git status` 中没有：

```text
.env
.venv/
db.sqlite3
__pycache__/
```

## 21. 最终检查

### 检查 Python 版本

```bash
uv run python --version
```

预期：

```text
Python 3.12.x
```

### 检查 Django 配置

```bash
uv run python manage.py check
```

预期：

```text
System check identified no issues (0 silenced).
```

### 检查迁移状态

```bash
uv run python manage.py migrate
```

如果迁移已全部执行，会看到：

```text
No migrations to apply.
```

## 22. 启动 API

```bash
uv run python manage.py runserver
```

访问：

```text
http://127.0.0.1:8000/api/tasks/
```

数据库没有任务时，响应是：

```json
[]
```

停止服务器：

```text
Ctrl + C
```

Django 自带的 `runserver` 只用于本地开发，不用于生产环境。

## 23. 验证 CRUD

保持服务器运行，并在另一个终端执行以下命令。

### 创建任务

```bash
curl -X POST http://127.0.0.1:8000/api/tasks/ \
  -H "Content-Type: application/json" \
  -d '{"title":"学习 Django","description":"创建第一条任务"}'
```

预期返回类似：

```json
{
  "id": 1,
  "title": "学习 Django",
  "description": "创建第一条任务",
  "completed": false,
  "created_at": "...",
  "updated_at": "..."
}
```

### 查询任务列表

```bash
curl http://127.0.0.1:8000/api/tasks/
```

### 查询单个任务

```bash
curl http://127.0.0.1:8000/api/tasks/1/
```

### 部分修改任务

```bash
curl -X PATCH http://127.0.0.1:8000/api/tasks/1/ \
  -H "Content-Type: application/json" \
  -d '{"completed":true}'
```

### 删除任务

```bash
curl -i -X DELETE http://127.0.0.1:8000/api/tasks/1/
```

成功时状态为：

```text
204 No Content
```

### 验证空标题校验

```bash
curl -i -X POST http://127.0.0.1:8000/api/tasks/ \
  -H "Content-Type: application/json" \
  -d '{"title":"   "}'
```

预期状态：

```text
400 Bad Request
```

预期响应：

```json
{"title":["标题不能为空。"]}
```

## 24. 最终项目结构

```text
todo-api/
├── .env                         # 本地真实配置，不提交
├── .env.example                 # 环境配置模板
├── .gitignore
├── .python-version              # Python 3.12
├── .venv/                       # 本地虚拟环境，不提交
├── README.md
├── apps/
│   ├── __init__.py
│   └── tasks/
│       ├── __init__.py
│       ├── admin.py
│       ├── apps.py
│       ├── migrations/
│       │   ├── __init__.py
│       │   └── 0001_initial.py
│       ├── models.py
│       ├── serializers.py
│       ├── tests.py
│       ├── urls.py
│       └── views.py
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── db.sqlite3                   # 本地数据库，不提交
├── manage.py
├── pyproject.toml
└── uv.lock
```

## 25. 常见问题

### `uv run python --version` 显示 Python 3.14

原因是 `requires-python = ">=3.12"` 允许更高版本，或者 `.venv` 之前由其他版本创建。

确认配置为：

```toml
requires-python = ">=3.12,<3.13"
```

然后执行：

```bash
uv python pin 3.12
uv venv --python 3.12 --clear
uv sync
uv run python --version
```

`--clear` 会重建 `.venv`，不会删除源码、`uv.lock` 或 `db.sqlite3`。

### 修改模型后数据库没有变化

修改 `models.py` 后必须依次执行：

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
```

### 提示缺少 `DJANGO_SECRET_KEY`

确认项目根目录存在 `.env`：

```env
DJANGO_SECRET_KEY=真实密钥
DJANGO_DEBUG=True
```

并确认 `config/settings.py` 已执行：

```python
environ.Env.read_env(BASE_DIR / ".env")
```

### 空标题仍返回英文提示

确认 `TaskSerializer.Meta` 中存在：

```python
extra_kwargs = {
    "title": {
        "error_messages": {
            "blank": "标题不能为空。",
        }
    }
}
```

DRF 会先执行字段基础校验，再执行 `validate_title()`。空字符串在基础校验阶段就会失败，因此 `blank` 的中文提示应在字段配置中设置。

## 26. 当前成果

完成以上步骤后，项目已经具备：

- 固定的 Python 3.12 运行环境
- uv 项目与依赖管理
- Django 系统配置层
- 独立的 tasks 业务模块
- SQLite 数据持久化
- 数据库迁移记录
- DRF 序列化器和输入校验
- RESTful CRUD API
- 环境变量与密钥隔离
- Git 忽略规则
- 可交接的配置模板与启动说明

后续可以逐步增加自动化测试、用户身份认证、任务归属、分页、搜索、过滤、PostgreSQL 和生产部署配置。
