#!/bin/bash

# VPS库存监控系统启动脚本

# 检查是否安装了Docker和Docker Compose
docker --version > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "错误: 未检测到Docker。请先安装Docker。"
    echo "安装指南: https://docs.docker.com/get-docker/"
    exit 1
fi

docker-compose --version > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "错误: 未检测到Docker Compose。请先安装Docker Compose。"
    echo "安装指南: https://docs.docker.com/compose/install/"
    exit 1
fi

# 打印启动信息
echo "========================================"
echo "        VPS库存监控系统启动脚本"
echo "========================================"
echo "此脚本将使用Docker Compose启动监控系统。"
echo ""
echo "启动前请确保您已配置.env文件中的必要参数。"
echo "默认情况下，系统将在http://localhost:5000上运行。"
echo ""
echo "管理员默认账户:"
echo "- 用户名: admin (可在.env文件中修改)"
echo "- 密码: password (可在.env文件中修改)"
echo "========================================"
echo ""

# 询问用户是否继续read -p "是否继续启动系统? (y/n): " choice
case "$choice" in 
  y|Y ) echo "正在启动系统...";
        ;;
  * ) echo "启动已取消。";
        exit 1;
        ;;
esac

# 创建数据目录mkdir -p data

# 启动Docker容器
docker-compose up -d --build

# 检查启动状态
sleep 5
docker-compose ps

# 显示日志命令提示
echo ""
echo "========================================"
echo "系统已启动!"
echo "访问地址: http://localhost:5000"
echo ""
echo "查看应用日志: docker-compose logs -f app"
echo "查看FlareSolverr日志: docker-compose logs -f flaresolverr"
echo "停止系统: docker-compose down"
echo "========================================"