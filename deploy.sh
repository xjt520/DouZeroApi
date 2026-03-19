#!/bin/bash

# DouZero API 自动部署脚本
# 适用于 CentOS 7

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
PYTHON_VERSION="3.9.18"
PYTHON_CMD="python3.9"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_NAME="douzero-api"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 权限运行此脚本: sudo bash $0"
        exit 1
    fi
}

# 检测系统
detect_system() {
    if [ -f /etc/centos-release ] || [ -f /etc/redhat-release ]; then
        SYSTEM="centos"
        log_info "检测到 CentOS/RHEL 系统"
    elif [ -f /etc/lsb-release ]; then
        SYSTEM="ubuntu"
        log_info "检测到 Ubuntu 系统"
    else
        log_warn "未识别的系统，尝试通用安装"
        SYSTEM="generic"
    fi
}

# 安装系统依赖
install_system_deps() {
    log_info "安装系统依赖..."
    
    if [ "$SYSTEM" = "centos" ]; then
        yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel wget curl make
    elif [ "$SYSTEM" = "ubuntu" ]; then
        apt-get update
        apt-get install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev \
            libnss3-dev libssl-dev libreadline-dev libffi-dev wget curl
    else
        log_warn "请手动安装: gcc, openssl-devel, libffi-devel, zlib-devel"
    fi
}

# 检查 Python 版本
check_python() {
    if command -v $PYTHON_CMD &> /dev/null; then
        local version=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
        log_info "已安装 $PYTHON_CMD 版本: $version"
        return 0
    fi
    return 1
}

# 安装 Python
install_python() {
    if check_python; then
        return 0
    fi
    
    log_info "开始安装 Python $PYTHON_VERSION..."
    
    local tmp_dir="/tmp/python_install"
    mkdir -p $tmp_dir
    cd $tmp_dir
    
    local url="https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tgz"
    
    if [ ! -f "Python-$PYTHON_VERSION.tgz" ]; then
        log_info "下载 Python $PYTHON_VERSION..."
        wget $url || {
            log_error "下载失败，尝试使用镜像..."
            # 尝试华为镜像
            url="https://mirrors.huaweicloud.com/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tgz"
            wget $url || {
                log_error "下载 Python 失败"
                exit 1
            }
        }
    fi
    
    log_info "解压..."
    tar -xzf Python-$PYTHON_VERSION.tgz
    cd Python-$PYTHON_VERSION
    
    log_info "配置..."
    ./configure --enable-optimizations --quiet
    
    log_info "编译安装 (这可能需要几分钟)..."
    make -j$(nproc) --quiet
    make altinstall --quiet
    
    # 验证安装
    if check_python; then
        log_info "Python $PYTHON_VERSION 安装成功"
        rm -rf $tmp_dir
    else
        log_error "Python 安装失败"
        exit 1
    fi
    
    cd $PROJECT_DIR
}

# 创建虚拟环境
create_venv() {
    log_info "创建虚拟环境..."
    
    # 删除旧的虚拟环境
    if [ -d "$VENV_DIR" ]; then
        log_warn "删除旧的虚拟环境..."
        rm -rf $VENV_DIR
    fi
    
    $PYTHON_CMD -m venv $VENV_DIR
    log_info "虚拟环境创建成功: $VENV_DIR"
}

# 安装 Python 依赖
install_python_deps() {
    log_info "安装 Python 依赖..."
    
    source $VENV_DIR/bin/activate
    
    # 升级 pip
    pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
    
    # 安装依赖
    if [ -f "$PROJECT_DIR/requirements_api.txt" ]; then
        pip install -r $PROJECT_DIR/requirements_api.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    else
        log_error "找不到 requirements_api.txt"
        exit 1
    fi
    
    log_info "Python 依赖安装完成"
}

# 检查模型文件
check_models() {
    log_info "检查模型文件..."
    
    local model_dir="$PROJECT_DIR/baselines/douzero_ADP"
    local models=("landlord.ckpt" "landlord_up.ckpt" "landlord_down.ckpt")
    local missing=0
    
    for model in "${models[@]}"; do
        if [ ! -f "$model_dir/$model" ]; then
            log_error "缺少模型文件: $model_dir/$model"
            missing=1
        fi
    done
    
    if [ $missing -eq 1 ]; then
        log_warn "请确保模型文件存在于 baselines/douzero_ADP/ 目录"
        read -p "是否继续部署? (y/n): " continue
        if [ "$continue" != "y" ]; then
            exit 1
        fi
    else
        log_info "模型文件检查通过"
    fi
}

# 创建 systemd 服务
create_systemd_service() {
    log_info "创建 systemd 服务..."
    
    # 获取实际运行用户（如果是 sudo 运行，使用 SUDO_USER）
    local run_user=${SUDO_USER:-$USER}
    
    cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=DouZero API Service
After=network.target

[Service]
Type=simple
User=$run_user
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/python api_server.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    log_info "systemd 服务创建成功"
}

# 配置防火墙
configure_firewall() {
    if command -v firewall-cmd &> /dev/null; then
        log_info "配置防火墙..."
        firewall-cmd --permanent --add-port=8000/tcp 2>/dev/null || true
        firewall-cmd --reload 2>/dev/null || true
        log_info "防火墙已开放 8000 端口"
    fi
}

# 启动服务
start_service() {
    log_info "启动服务..."
    
    systemctl start $SERVICE_NAME
    systemctl enable $SERVICE_NAME
    
    sleep 3
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        log_info "服务启动成功"
    else
        log_error "服务启动失败，查看日志:"
        journalctl -u $SERVICE_NAME -n 20 --no-pager
        exit 1
    fi
}

# 显示状态
show_status() {
    echo ""
    echo "=========================================="
    log_info "部署完成!"
    echo "=========================================="
    echo ""
    echo "服务状态:"
    systemctl status $SERVICE_NAME --no-pager | head -10
    echo ""
    echo "测试访问:"
    echo "  curl http://localhost:8000/api/health"
    echo ""
    echo "API 文档:"
    echo "  http://<服务器IP>:8000/docs"
    echo ""
    echo "常用命令:"
    echo "  查看状态: systemctl status $SERVICE_NAME"
    echo "  查看日志: journalctl -u $SERVICE_NAME -f"
    echo "  重启服务: systemctl restart $SERVICE_NAME"
    echo "  停止服务: systemctl stop $SERVICE_NAME"
    echo ""
}

# 主函数
main() {
    echo ""
    echo "=========================================="
    echo "  DouZero API 自动部署脚本"
    echo "=========================================="
    echo ""
    
    check_root
    detect_system
    install_system_deps
    install_python
    create_venv
    install_python_deps
    check_models
    create_systemd_service
    configure_firewall
    start_service
    show_status
}

# 运行
main
