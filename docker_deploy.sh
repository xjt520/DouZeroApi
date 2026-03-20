#!/bin/bash

# DouZero API Docker 部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE_NAME="douzero-api"
CONTAINER_NAME="douzero-api"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker 是否安装
check_docker() {
    if ! docker version &> /dev/null; then
        log_error "Docker 未安装或未启动"
        exit 1
    fi
    
    # 优先使用 docker compose (Plugin)
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        log_error "Docker Compose 未安装"
        exit 1
    fi
    
    log_info "Docker 环境检查通过: $(docker --version)"
    log_info "使用命令: $DOCKER_COMPOSE"
}

# 检查模型文件
check_models() {
    log_info "检查模型文件..."
    
    local model_dir="$PROJECT_DIR/baselines"
    if [ ! -d "$model_dir" ] || [ -z "$(ls -A $model_dir)" ]; then
        log_error "缺少模型目录或目录为空: $model_dir"
        log_warn "请确保预训练模型已放置在 baselines/ 目录下"
        exit 1
    fi
    log_info "模型目录检查通过"
}

# 构建镜像
build_image() {
    log_info "构建 Docker 镜像..."
    cd "$PROJECT_DIR"
    $DOCKER_COMPOSE build
    log_info "镜像构建完成"
}

# 启动服务
start_service() {
    log_info "启动服务..."
    cd "$PROJECT_DIR"
    mkdir -p logs
    $DOCKER_COMPOSE up -d
    
    log_info "等待容器启动并进行健康检查..."
    local count=0
    local max_retries=10
    while [ $count -lt $max_retries ]; do
        if docker ps | grep -q "$CONTAINER_NAME" && [ "$(docker inspect -f '{{.State.Health.Status}}' $CONTAINER_NAME 2>/dev/null)" == "healthy" ]; then
            log_info "服务启动成功且健康检查通过"
            return 0
        fi
        echo -n "."
        sleep 3
        ((count++))
    done
    
    echo ""
    log_warn "服务启动超时或健康检查未通过，请手动检查: docker ps"
}

# 停止服务
stop_service() {
    log_info "停止服务..."
    cd "$PROJECT_DIR"
    $DOCKER_COMPOSE down
    log_info "服务已停止"
}

# 重启服务
restart_service() {
    log_info "重启服务..."
    cd "$PROJECT_DIR"
    $DOCKER_COMPOSE restart
    log_info "服务已重启"
}

# 查看日志
view_logs() {
    docker logs -f $CONTAINER_NAME
}

# 查看状态
show_status() {
    echo ""
    echo "=========================================="
    log_info "Docker 部署状态"
    echo "=========================================="
    echo ""
    
    docker ps -a | grep $CONTAINER_NAME || echo "容器未运行"
    
    echo ""
    echo "测试访问:"
    echo "  curl http://localhost:8000/api/health"
    echo ""
    echo "API 文档:"
    echo "  http://localhost:8000/docs"
    echo ""
    echo "常用命令:"
    echo "  查看日志: ./docker_deploy.sh logs"
    echo "  重启服务: ./docker_deploy.sh restart"
    echo "  停止服务: ./docker_deploy.sh stop"
    echo "  启动服务: ./docker_deploy.sh start"
    echo "  重新构建: ./docker_deploy.sh rebuild"
    echo ""
}

# 重新构建并启动
rebuild() {
    stop_service
    build_image
    start_service
    show_status
}

# 显示帮助
show_help() {
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  deploy    - 完整部署（构建镜像并启动服务）"
    echo "  start     - 启动服务"
    echo "  stop      - 停止服务"
    echo "  restart   - 重启服务"
    echo "  rebuild   - 重新构建并启动"
    echo "  logs      - 查看日志"
    echo "  status    - 查看状态"
    echo "  help      - 显示帮助"
    echo ""
}

# 主函数
main() {
    local command=${1:-deploy}
    
    case $command in
        deploy)
            echo ""
            echo "=========================================="
            echo "  DouZero API Docker 部署"
            echo "=========================================="
            echo ""
            check_docker
            check_models
            build_image
            start_service
            show_status
            ;;
        start)
            check_docker
            start_service
            show_status
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service
            show_status
            ;;
        rebuild)
            check_docker
            check_models
            rebuild
            ;;
        logs)
            view_logs
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 运行
main "$@"
