# 用户认证服务 API 文档

## 服务地址

**线上地址**: `https://ai-python-3x1q.onrender.com`

---

## 接口列表

| 接口路径 | HTTP方法 | 功能描述 |
|---------|---------|---------|
| `/` | GET | 健康检查 |
| `/register` | POST | 用户注册 |
| `/login` | POST | 用户登录 |
| `/user/profile` | GET | 获取用户信息 |
| `/verify-token` | POST | 验证Token |

---

## 接口详情

### 1. 健康检查

**接口地址**: `GET /`

**功能描述**: 检查服务是否正常运行

**请求示例**:
```bash
curl https://ai-python-3x1q.onrender.com/
```

**成功响应** (200 OK):
```json
{
  "status": "ok",
  "service": "user-auth-service"
}
```

---

### 2. 用户注册

**接口地址**: `POST /register`

**功能描述**: 新用户注册

**请求参数**:

| 参数名 | 类型 | 必填 | 描述 |
|-------|------|-----|------|
| username | string | 是 | 用户名，长度至少3个字符 |
| password | string | 是 | 密码，长度至少6个字符 |
| email | string | 否 | 邮箱地址 |
| phone | string | 否 | 手机号码 |

**请求示例**:
```bash
curl -X POST https://ai-python-3x1q.onrender.com/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "123456",
    "email": "john@example.com",
    "phone": "13800138000"
  }'
```

**成功响应** (200 OK):
```json
{
  "success": true,
  "user_id": "979872",
  "username": "john_doe",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "注册成功"
}
```

**失败响应** (400 Bad Request):
```json
{
  "success": false,
  "error": "username_exists",
  "message": "用户名已存在"
}
```

---

### 3. 用户登录

**接口地址**: `POST /login`

**功能描述**: 用户登录获取Token

**请求参数**:

| 参数名 | 类型 | 必填 | 描述 |
|-------|------|-----|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**请求示例**:
```bash
curl -X POST https://ai-python-3x1q.onrender.com/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "123456"
  }'
```

**成功响应** (200 OK):
```json
{
  "success": true,
  "user_id": "979872",
  "username": "john_doe",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "登录成功"
}
```

**失败响应** (401 Unauthorized):
```json
{
  "success": false,
  "error": "wrong_password",
  "message": "密码错误"
}
```

---

### 4. 获取用户信息

**接口地址**: `GET /user/profile`

**功能描述**: 获取当前登录用户的详细信息，需要携带Token

**请求头**:

| 头部名 | 值格式 | 必填 | 描述 |
|-------|--------|-----|------|
| Authorization | Bearer {token} | 是 | JWT令牌 |

**请求示例**:
```bash
curl -X GET https://ai-python-3x1q.onrender.com/user/profile \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**成功响应** (200 OK):
```json
{
  "success": true,
  "user": {
    "user_id": "979872",
    "username": "john_doe",
    "email": "john@example.com",
    "phone": "13800138000",
    "created_at": "2026-05-13 07:58:02",
    "last_login": "2026-05-13 08:15:30"
  }
}
```

**失败响应** (401 Unauthorized):
```json
{
  "error": "invalid_token",
  "message": "无效或已过期的令牌"
}
```

---

### 5. 验证Token

**接口地址**: `POST /verify-token`

**功能描述**: 验证Token的有效性

**请求参数**:

| 参数名 | 类型 | 必填 | 描述 |
|-------|------|-----|------|
| token | string | 是 | JWT令牌 |

**请求示例**:
```bash
curl -X POST https://ai-python-3x1q.onrender.com/verify-token \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**成功响应** (200 OK):
```json
{
  "success": true,
  "valid": true,
  "user_id": "979872",
  "username": "john_doe",
  "email": "john@example.com",
  "phone": "13800138000"
}
```

**失败响应** (200 OK):
```json
{
  "success": false,
  "valid": false,
  "error": "token_expired",
  "message": "Token无效或已过期"
}
```

---

## 错误码说明

| 错误码 | 含义 | HTTP状态码 |
|-------|------|-----------|
| `username_too_short` | 用户名长度不足 | 400 |
| `password_too_short` | 密码长度不足 | 400 |
| `username_exists` | 用户名已存在 | 400 |
| `user_not_found` | 用户不存在 | 401 |
| `wrong_password` | 密码错误 | 401 |
| `missing_token` | 未提供令牌 | 401 |
| `invalid_token_format` | 令牌格式错误 | 401 |
| `invalid_token` | 无效令牌 | 401 |
| `token_expired` | 令牌已过期 | 200 |
| `database_error` | 数据库错误 | 500 |

---

## 使用流程示例

```bash
# 1. 注册新用户
curl -X POST https://ai-python-3x1q.onrender.com/register \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "123456"}'

# 响应: {"success":true,"user_id":"123456","token":"xxx...","message":"注册成功"}

# 2. 使用Token访问受保护接口
curl -X GET https://ai-python-3x1q.onrender.com/user/profile \
  -H "Authorization: Bearer xxx..."
```

---

## 技术栈

- **框架**: FastAPI 0.110+
- **数据库**: SQLite
- **认证**: JWT (PyJWT)
- **部署**: Render