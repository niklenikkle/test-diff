#!/bin/bash

echo "========================================"
echo "Django 数据库查询服务启动脚本"
echo "========================================"

echo ""
echo "[1/4] 安装依赖..."
pip install -r requirements.txt

echo ""
echo "[2/4] 执行数据库迁移..."
python manage.py makemigrations
python manage.py migrate

echo ""
echo "[3/4] 初始化知识库数据..."
python manage.py init_knowledge

echo ""
echo "[4/4] 创建超级管理员..."
python manage.py createsuperuser --noinput 2>/dev/null || echo "管理员已存在或跳过创建"

echo ""
echo "========================================"
echo "启动开发服务器..."
echo "========================================"
python manage.py runserver 0.0.0.0:8000
