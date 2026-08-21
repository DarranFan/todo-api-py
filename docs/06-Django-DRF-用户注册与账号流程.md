# Django DRF 用户注册与账号流程

本文承接已经完成 Token 认证和用户数据隔离的 Todo API，补齐用户注册、登录、修改密码和退出登录功能。

## 这章到底讲什么

上一阶段虽然已经可以使用 Token 登录，但用户必须由开发者通过 Django Shell 创建。

本章把账号流程开放成真正可供客户端使用的 API：

```text
注册
POST /api/register/
    ↓
登录获取 Token
POST /api/token/
    ↓
携带 Token 使用业务接口
    ↓
修改密码或退出登录
    ↓
旧 Token 失效
```

最终提供：

```text
POST /api/register/          注册
POST /api/token/             登录并获取 Token
POST /api/change-password/   修改密码
POST /api/logout/            退出并删除 Token
```

## 1. 创建用户为什么不能使用普通 create

密码不能作为普通字符串直接保存：

```python
User.objects.create(
    username="alice",
    password="Alice123456!",
)
```

这种写法不会正确生成 Django 密码哈希。

必须使用：

```python
User.objects.create_user(
    username="alice",
    password="Alice123456!",
)
```

修改已有用户密码时则必须使用：

```python
user.set_password(new_password)
user.save()
```

核心原则：

```text
创建用户      create_user()
修改密码      set_password()
不要直接赋值  user.password = "明文密码"
```

## 2. UserSerializer

在 `apps/tasks/serializers.py` 中导入：

```python
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
```

取得当前用户模型：

```python
User = get_user_model()
```

创建注册 Serializer：

```python
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
```

关键配置：

```text
write_only=True               密码可以提交，但不会出现在响应中
validators=[validate_password] 使用 Django 密码强度规则
read_only_fields=["id"]        ID 由数据库生成
create_user()                  加密并保存密码
```

注册请求：

```json
{
  "username": "dave",
  "password": "Violet-River-82!"
}
```

成功响应不会返回密码：

```json
{
  "id": 3,
  "username": "dave"
}
```

## 3. 公开注册 View

在 `apps/tasks/views.py` 中添加：

```python
class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
```

各项作用：

```text
CreateAPIView              只提供 POST 创建功能
UserSerializer             校验并创建用户
AllowAny                   未登录用户也能注册
authentication_classes=[]  注册接口不要求处理 Token
```

项目全局权限是 `IsAuthenticated`，但注册发生在登录之前，所以这个接口必须单独使用 `AllowAny`。

## 4. 注册路由为什么使用 path

在 `apps/tasks/urls.py` 中添加：

```python
path("register/", UserRegistrationView.as_view(), name="register")
```

`TaskViewSet` 和 `CategoryViewSet` 使用 Router，是因为它们提供一组 CRUD 操作。

注册 View 只提供一条 POST 接口，所以使用普通 `path()`：

```text
router.register()  为 ViewSet 自动生成一组 URL
path()             为普通 View 注册一条明确 URL
```

最终地址：

```text
POST /api/register/
```

## 5. 验证注册

```bash
curl -i -X POST \
  "http://127.0.0.1:8000/api/register/" \
  -H "Content-Type: application/json" \
  -d '{"username":"dave","password":"Violet-River-82!"}'
```

预期：

```http
201 Created
```

重复用户名或弱密码返回：

```http
400 Bad Request
```

## 6. 登录获取 Token

登录接口由 DRF 的 `obtain_auth_token` 提供：

```text
POST /api/token/
```

请求：

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/token/" \
  -H "Content-Type: application/json" \
  -d '{"username":"dave","password":"Violet-River-82!"}'
```

响应：

```json
{
  "token": "实际Token"
}
```

后续请求携带：

```text
Authorization: Token 实际Token
```

## 7. 修改密码 Serializer

修改密码需要两个输入字段：

```python
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
```

两个字段都设置 `write_only=True`，因此不会进入 API 响应。

### 校验原密码

```python
def validate_old_password(self, value):
    user = self.context["request"].user

    if not user.check_password(value):
        raise serializers.ValidationError("原密码不正确。")

    return value
```

`check_password()` 会使用 Django 的密码哈希机制检查输入，不能直接比较密码字符串。

### 校验新密码

```python
def validate_new_password(self, value):
    user = self.context["request"].user
    validate_password(value, user=user)
    return value
```

这里会使用 Django 配置的密码强度规则。

### 保存新密码

```python
def save(self):
    user = self.context["request"].user
    user.set_password(self.validated_data["new_password"])
    user.save(update_fields=["password"])
    return user
```

`set_password()` 负责生成新的密码哈希，`update_fields` 表示这次只更新密码字段。

## 8. 修改密码 View

```python
class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        request.auth.delete()

        return Response(
            {"detail": "密码修改成功，请重新登录。"},
            status=status.HTTP_200_OK,
        )
```

请求链路：

```text
有效 Token
    ↓
找到 request.user
    ↓
校验旧密码和新密码
    ↓
set_password() 保存新密码
    ↓
request.auth.delete() 删除当前 Token
    ↓
要求重新登录
```

修改密码后删除 Token，可以避免旧登录凭证继续使用。

## 9. 修改密码路由与请求

路由：

```python
path(
    "change-password/",
    ChangePasswordView.as_view(),
    name="change-password",
)
```

请求：

```bash
curl -i -X POST \
  "http://127.0.0.1:8000/api/change-password/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token 这里填写当前Token" \
  -d '{"old_password":"Violet-River-82!","new_password":"Golden-Cloud-93!"}'
```

成功响应：

```json
{
  "detail": "密码修改成功，请重新登录。"
}
```

旧 Token 随后返回 `401 Unauthorized`。使用新密码调用 `/api/token/` 可以取得新 Token。

## 10. 退出登录 View

```python
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.auth.delete()

        return Response(
            {"detail": "退出登录成功。"},
            status=status.HTTP_200_OK,
        )
```

这里：

```text
request.user  当前 Token 对应的用户
request.auth  当前请求使用的 Token 对象
```

删除 `request.auth` 后，客户端保存的旧 Token 无法继续认证。

## 11. 退出登录路由与请求

路由：

```python
path("logout/", LogoutView.as_view(), name="logout")
```

请求：

```bash
curl -i -X POST \
  "http://127.0.0.1:8000/api/logout/" \
  -H "Authorization: Token 这里填写实际Token"
```

成功响应：

```json
{
  "detail": "退出登录成功。"
}
```

再次使用旧 Token 访问业务接口，预期：

```http
401 Unauthorized
```

## 12. 完整账号流程

```text
1. POST /api/register/
   创建用户并加密保存密码

2. POST /api/token/
   使用用户名和密码获取 Token

3. Authorization: Token ...
   访问 Task 和 Category 接口

4A. POST /api/change-password/
    修改密码并删除旧 Token

4B. POST /api/logout/
    删除当前 Token

5. POST /api/token/
   重新登录并获取新 Token
```

## 13. 安全边界

当前实现遵循以下规则：

- 注册接口允许匿名访问。
- Task、Category、改密和退出接口要求登录。
- 密码字段只写，不在响应中返回。
- 密码通过 `create_user()` 或 `set_password()` 加密处理。
- 修改密码前必须验证旧密码。
- 修改密码和退出登录都会让当前 Token 失效。
- Token 不应提交到源码、文档或 Git。
- 正式环境必须通过 HTTPS 传输 Token 和密码。

## 14. 最终检查

```bash
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```

预期：

```text
System check identified no issues (0 silenced).
No changes detected
```

这一阶段只增加 Serializer、View 和 URL，没有修改模型，因此不需要新的数据库迁移。

至此，Todo API 已经具备可以由客户端完整使用的注册、登录、改密和退出流程。
