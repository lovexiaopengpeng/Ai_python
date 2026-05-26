from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, Dict
import sqlite3
import jwt
import datetime
import os
from pathlib import Path

DATABASE_PATH = Path("./user_database.db")
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here_change_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
DATABASE_URL = os.getenv("DATABASE_URL")

DB_TYPE = "sqlite"
if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
    DB_TYPE = "postgresql"
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        DB_TYPE = "sqlite"

app = FastAPI(title="用户认证服务", description="提供用户注册、登录和Token验证服务")

def get_db_connection():
    if DB_TYPE == "postgresql" and DATABASE_URL:
        try:
            return psycopg2.connect(DATABASE_URL, sslmode="require")
        except Exception as e:
            print(f"PostgreSQL连接失败，回退到SQLite: {e}")
    
    return sqlite3.connect(str(DATABASE_PATH))

def init_database():
    conn = get_db_connection()
    
    if DB_TYPE == "postgresql":
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """
    
    try:
        cursor.execute(create_table_sql)
        conn.commit()
        print(f"✅ 用户数据库初始化完成 ({DB_TYPE})")
    except Exception as e:
        print(f"数据库初始化错误: {e}")
    finally:
        conn.close()

def generate_token(user_id: str, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        "iat": datetime.datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def verify_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("username"),
            "valid": True
        }
    except jwt.ExpiredSignatureError:
        return {"valid": False, "error": "token_expired"}
    except jwt.InvalidTokenError:
        return {"valid": False, "error": "invalid_token"}

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str = ""
    phone: str = ""

class LoginRequest(BaseModel):
    username: str
    password: str
    device_type: Optional[str] = None
    imei: Optional[str] = None
    notification_token: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str

class DeleteAccountRequest(BaseModel):
    username: str
    password: str

def generate_user_id() -> str:
    import random
    return str(random.randint(1000, 999999))

def db_execute(cursor, query, params=()):
    if DB_TYPE == "postgresql":
        cursor.execute(query, params)
    else:
        query = query.replace("%s", "?")
        cursor.execute(query, params)

@app.post("/register", summary="用户注册")
def register(req: RegisterRequest):
    if not req.username or len(req.username) < 3:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "username_too_short",
                "message": "用户名长度至少为3个字符"
            }
        )
    
    if not req.password or len(req.password) < 6:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "password_too_short",
                "message": "密码长度至少为6个字符"
            }
        )
    
    conn = get_db_connection()
    
    if DB_TYPE == "postgresql":
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    try:
        db_execute(cursor, "SELECT user_id FROM users WHERE username = %s", (req.username,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "username_exists",
                    "message": "用户名已存在"
                }
            )
        
        user_id = generate_user_id()
        
        db_execute(cursor, "INSERT INTO users (user_id, username, password, email, phone) VALUES (%s, %s, %s, %s, %s)",
                       (user_id, req.username, req.password, req.email, req.phone))
        
        conn.commit()
        token = generate_token(user_id, req.username)
        
        print(f"✅ 用户注册成功: {req.username}, ID: {user_id}")
        
        return {
            "success": True,
            "user_id": user_id,
            "username": req.username,
            "token": token,
            "message": "注册成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "database_error",
                "message": f"数据库错误: {str(e)}"
            }
        )
    finally:
        conn.close()

@app.post("/login", summary="用户登录")
def login(req: LoginRequest):
    conn = get_db_connection()
    
    if DB_TYPE == "postgresql":
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    try:
        db_execute(cursor, "SELECT user_id, username, password FROM users WHERE username = %s", (req.username,))
        
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail={
                    "success": False,
                    "error": "user_not_found",
                    "message": "用户名不存在"
                }
            )
        
        user_id, stored_username, stored_password = user
        
        if req.password != stored_password:
            raise HTTPException(
                status_code=401,
                detail={
                    "success": False,
                    "error": "wrong_password",
                    "message": "密码错误"
                }
            )
        
        if req.device_type == "android" and not req.imei:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "missing_imei",
                    "message": "安卓设备需要提供IMEI"
                }
            )
        
        if req.device_type == "ios" and not req.notification_token:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "missing_notification_token",
                    "message": "iOS设备需要提供通知Token"
                }
            )
        
        db_execute(cursor, "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s", (user_id,))
        conn.commit()
        
        token = generate_token(user_id, req.username)
        
        print(f"✅ 用户登录成功: {req.username}, ID: {user_id}, 设备类型: {req.device_type}")
        
        return {
            "success": True,
            "user_id": user_id,
            "username": req.username,
            "token": token,
            "message": "登录成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "database_error",
                "message": f"数据库错误: {str(e)}"
            }
        )
    finally:
        conn.close()

@app.post("/reset-password", summary="重置密码")
def reset_password(req: ResetPasswordRequest):
    if not req.new_password or len(req.new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "password_too_short",
                "message": "新密码长度至少为6个字符"
            }
        )
    
    conn = get_db_connection()
    
    if DB_TYPE == "postgresql":
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    try:
        db_execute(cursor, "SELECT user_id, username, password FROM users WHERE username = %s", (req.username,))
        
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": "user_not_found",
                    "message": "用户名不存在"
                }
            )
        
        user_id, stored_username, stored_password = user
        
        if req.old_password != stored_password:
            raise HTTPException(
                status_code=401,
                detail={
                    "success": False,
                    "error": "wrong_password",
                    "message": "原密码错误"
                }
            )
        
        db_execute(cursor, "UPDATE users SET password = %s WHERE user_id = %s", (req.new_password, user_id))
        conn.commit()
        
        print(f"✅ 用户密码重置成功: {req.username}, ID: {user_id}")
        
        return {
            "success": True,
            "message": "密码重置成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "database_error",
                "message": f"数据库错误: {str(e)}"
            }
        )
    finally:
        conn.close()

def get_current_user(authorization: str = Header(None)) -> Dict:
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={"error": "missing_token", "message": "未提供认证令牌"}
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token_format", "message": "令牌格式错误"}
        )
    
    token = authorization[7:]
    payload = verify_token(token)
    
    if not payload.get("valid"):
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "message": "无效或已过期的令牌"}
        )
    
    return payload

@app.get("/user/profile", summary="获取用户信息")
def get_user_profile(current_user: Dict = Depends(get_current_user)):
    conn = get_db_connection()
    
    if DB_TYPE == "postgresql":
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    try:
        db_execute(cursor, "SELECT user_id, username, email, phone, created_at, last_login FROM users WHERE user_id = %s",
                       (current_user["user_id"],))
        
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail={"success": False, "message": "用户不存在"}
            )
        
        return {
            "success": True,
            "user": {
                "user_id": user[0],
                "username": user[1],
                "email": user[2],
                "phone": user[3],
                "created_at": str(user[4]),
                "last_login": str(user[5])
            }
        }
        
    finally:
        conn.close()

@app.post("/user/delete", summary="注销用户账户")
def delete_user(req: DeleteAccountRequest):
    conn = get_db_connection()
    
    if DB_TYPE == "postgresql":
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    try:
        db_execute(cursor, "SELECT user_id, username, password FROM users WHERE username = %s", (req.username,))
        
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": "user_not_found",
                    "message": "用户名不存在"
                }
            )
        
        user_id, stored_username, stored_password = user
        
        if req.password != stored_password:
            raise HTTPException(
                status_code=401,
                detail={
                    "success": False,
                    "error": "wrong_password",
                    "message": "密码错误"
                }
            )
        
        db_execute(cursor, "DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        
        print(f"✅ 用户账户已注销: {req.username}, ID: {user_id}")
        
        return {
            "success": True,
            "message": "账户注销成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "database_error",
                "message": f"数据库错误: {str(e)}"
            }
        )
    finally:
        conn.close()

class TokenRequest(BaseModel):
    token: str

@app.post("/verify-token", summary="验证Token")
def verify_token_endpoint(req: TokenRequest):
    result = verify_token(req.token)
    
    if not result.get("valid"):
        return {
            "success": False,
            "valid": False,
            "error": result.get("error"),
            "message": "Token无效或已过期"
        }
    
    conn = get_db_connection()
    
    if DB_TYPE == "postgresql":
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    try:
        db_execute(cursor, "SELECT user_id, username, email, phone FROM users WHERE user_id = %s", (result["user_id"],))
        
        user = cursor.fetchone()
        
        if user:
            return {
                "success": True,
                "valid": True,
                "user_id": user[0],
                "username": user[1],
                "email": user[2],
                "phone": user[3]
            }
        else:
            return {
                "success": False,
                "valid": False,
                "error": "user_not_found",
                "message": "用户不存在"
            }
        
    finally:
        conn.close()

@app.get("/admin/users", summary="获取所有用户列表")
def get_all_users():
    conn = get_db_connection()
    
    if DB_TYPE == "postgresql":
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    try:
        db_execute(cursor, "SELECT user_id, username, email, phone, created_at, last_login FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        
        user_list = []
        for user in users:
            user_list.append({
                "user_id": user[0],
                "username": user[1],
                "email": user[2],
                "phone": user[3],
                "created_at": str(user[4]),
                "last_login": str(user[5]) if user[5] else None
            })
        
        return {"success": True, "total": len(user_list), "users": user_list}
    finally:
        conn.close()

@app.get("/", summary="健康检查")
def health_check():
    return {"status": "ok", "service": "user-auth-service", "db_type": DB_TYPE}

init_database()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
