#!/usr/bin/env python3
"""
简易FastAPI部署脚本
在服务器上直接运行即可
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def print_step(step: int, message: str):
    print(f"\n{'='*60}")
    print(f" 步骤 {step}: {message}")
    print(f"{'='*60}\n")

def run_command(cmd: str, cwd: str = None):
    """运行命令并返回结果"""
    print(f"$ {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"错误: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"执行错误: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("  FastAPI 项目简易部署工具")
    print("="*60 + "\n")
    
    # 配置
    PROJECT_DIR = Path("/www/wwwroot/fastapi-project")
    VENV_DIR = PROJECT_DIR / "venv"
    
    # 步骤1: 创建项目目录
    print_step(1, "创建项目目录")
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    os.chdir(PROJECT_DIR)
    print(f"当前目录: {os.getcwd()}")
    
    # 步骤2: 检查文件
    print_step(2, "检查项目文件")
    required_files = ["main.py", "requirements.txt"]
    for file in required_files:
        if not (PROJECT_DIR / file).exists():
            print(f"⚠️  警告: {file} 不存在，请先上传项目文件！")
            print(f"   请将项目文件上传到: {PROJECT_DIR}")
            return 1
        print(f"✅ {file} 已就绪")
    
    # 步骤3: 创建虚拟环境
    print_step(3, "创建Python虚拟环境")
    if not VENV_DIR.exists():
        if run_command("python3 -m venv venv"):
            print("✅ 虚拟环境创建成功")
        else:
            print("❌ 虚拟环境创建失败")
            return 1
    else:
        print("✅ 虚拟环境已存在")
    
    # 步骤4: 升级pip和安装依赖
    print_step(4, "安装项目依赖")
    pip_path = VENV_DIR / "bin" / "pip"
    if run_command(f"{pip_path} install --upgrade pip"):
        print("✅ pip升级成功")
    
    if run_command(f"{pip_path} install -r requirements.txt"):
        print("✅ 依赖安装成功")
    else:
        print("❌ 依赖安装失败")
        return 1
    
    # 步骤5: 测试运行
    print_step(5, "测试项目")
    python_path = VENV_DIR / "bin" / "python"
    
    print("\n" + "="*60)
    print("  部署基本完成！")
    print("="*60 + "\n")
    print("接下来请执行以下操作：")
    print("\n1. 手动运行测试（在screen中）：")
    print(f"   cd {PROJECT_DIR}")
    print(f"   {python_path} -m uvicorn main:app --host 0.0.0.0 --port 8000")
    
    print("\n2. 配置宝塔面板的Python项目管理器（推荐）")
    print("   - 在宝塔面板安装 Python项目管理器")
    print("   - 然后在宝塔面板中配置项目")
    
    print("\n3. 访问地址：")
    print("   - http://111.230.110.33:8000")
    print("   - http://111.230.110.33:8000/docs")
    
    print("\n" + "="*60 + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
