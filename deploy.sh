#!/bin/bash
# FastAPI 项目一键部署脚本

echo "==================================="
echo "  FastAPI 项目一键部署脚本"
echo "==================================="

# 配置
PROJECT_DIR="/www/wwwroot/fastapi-project"
VENV_DIR="$PROJECT_DIR/venv"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
MAIN_FILE="$PROJECT_DIR/main.py"
SERVICE_NAME="fastapi-project"
PORT=8000

# 检查是否是root用户
if [ "$EUID" -ne 0 ]
  then echo "请使用root权限运行此脚本"
  exit
fi

echo ""
echo "1. 创建项目目录..."
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

echo ""
echo "2. 检查当前目录..."
pwd
ls -la

echo ""
echo "3. 创建Python虚拟环境..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
    echo "   虚拟环境创建成功"
else
    echo "   虚拟环境已存在"
fi

echo ""
echo "4. 激活虚拟环境..."
source $VENV_DIR/bin/activate

echo ""
echo "5. 升级pip..."
pip install --upgrade pip

echo ""
echo "6. 安装项目依赖..."
if [ -f "$REQUIREMENTS_FILE" ]; then
    pip install -r $REQUIREMENTS_FILE
    echo "   依赖安装成功"
else
    echo "   警告: requirements.txt文件不存在"
fi

echo ""
echo "7. 检查项目文件..."
ls -la

echo ""
echo "8. 创建systemd服务文件..."
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=FastAPI Application
After=network.target

[Service]
Type=notify
User=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/python -m uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "9. 重新加载systemd..."
systemctl daemon-reload

echo ""
echo "10. 启用服务..."
systemctl enable $SERVICE_NAME

echo ""
echo "11. 启动服务..."
systemctl start $SERVICE_NAME

echo ""
echo "12. 检查服务状态..."
systemctl status $SERVICE_NAME

echo ""
echo "==================================="
echo "  部署完成！"
echo "==================================="
echo ""
echo "服务名称: $SERVICE_NAME"
echo "服务状态: systemctl status $SERVICE_NAME"
echo "启动服务: systemctl start $SERVICE_NAME"
echo "停止服务: systemctl stop $SERVICE_NAME"
echo "重启服务: systemctl restart $SERVICE_NAME"
echo "查看日志: journalctl -u $SERVICE_NAME -f"
echo ""
echo "访问地址: http://111.230.110.33:$PORT"
echo "API文档: http://111.230.110.33:$PORT/docs"
echo ""
