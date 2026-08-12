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

复制配置模板：

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
