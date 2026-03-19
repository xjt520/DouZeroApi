# DouZero API 服务

基于 FastAPI 的斗地主 AI 接口服务，提供出牌、叫分、加倍建议。

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements_api.txt
```

### 2. 启动服务

```bash
python3 api_server.py
```

服务将在 `http://localhost:8000` 启动。

### 3. 访问 API 文档

浏览器打开：`http://localhost:8000/docs`

---

## 📋 API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 服务信息 |
| `/api/health` | GET | 健康检查 |
| `/api/config` | GET | 获取模型配置 |
| `/api/play` | POST | 获取最佳出牌建议 |
| `/api/actions` | POST | 获取所有出牌建议及排序 |
| `/api/bid` | POST | 获取叫分建议 |
| `/api/double` | POST | 获取加倍建议 |
| `/docs` | GET | Swagger API 文档 |

---

## 🎴 牌值格式

API 使用字符串格式表示牌：

| 字符 | 牌面 |
|------|------|
| 3-9 | 3-9 |
| T | 10 |
| J | J |
| Q | Q |
| K | K |
| A | A |
| 2 | 2 |
| X | 小王 |
| D | 大王 |

示例：`"3456789TJQKA2XD"` 表示 3-A 的顺子 + 2 + 小王 + 大王

---

## 🎯 API 使用示例

### 1. 健康检查

```bash
curl http://localhost:8000/api/health
```

**响应**：
```json
{
  "status": "healthy",
  "agent_initialized": true
}
```

---

### 2. 获取最佳出牌建议

```bash
curl -X POST http://localhost:8000/api/play \
  -H "Content-Type: application/json" \
  -d '{
    "position": "landlord",
    "my_cards": "568AJ2",
    "played_cards": {
      "landlord": "34",
      "landlord_up": "7",
      "landlord_down": ""
    },
    "last_moves": ["7", "5"],
    "landlord_cards": "2XD",
    "cards_left": {
      "landlord": 6,
      "landlord_up": 16,
      "landlord_down": 17
    },
    "bomb_count": 0
  }'
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `position` | string | ✅ | 玩家位置: `landlord`, `landlord_up`, `landlord_down` |
| `my_cards` | string | ✅ | 玩家手牌 (如 "3456789TJQKA2XD") |
| `played_cards` | object | ⚠️ | **全量累计**已出牌 {"landlord": "345", "landlord_up": "67", "landlord_down": "89"}，见下方重要说明 |
| `last_moves` | array | ❌ | 最近几轮出牌 (如 ["3", "5"])，用于判断当前轮次 |
| `landlord_cards` | string | ❌ | 地主底牌 |
| `cards_left` | object | ⚠️ | 各位置剩余牌数 {"landlord": 15, "landlord_up": 10, "landlord_down": 17} |
| `bomb_count` | int | ❌ | 已出炸弹数量 |
| `bid_info` | array | ❌ | 叫分信息矩阵 |
| `multiply_info` | array | ❌ | 加倍信息 |

> ⚠️ **关于 `played_cards` 和 `cards_left` 的重要说明**：
> 
> 模型需要推断对手的剩余手牌，这依赖于准确的已出牌信息：
> - `played_cards` 必须是**全量累计**（从开局到当前该位置打出的所有牌），**不能只传最近一轮**
> - 如果你的系统无法维护全量 `played_cards`，**务必提供 `cards_left`**（各位置剩余牌数）
> - 若 `played_cards` 不完整且未提供 `cards_left`，模型会将已出的牌误判为对手手牌，导致推理**严重失准**
>
> **最佳实践**：同时提供准确的 `played_cards`（全量）和 `cards_left`

**响应**：
```json
{
  "cards": "8",
  "win_rate": 0.85,
  "action_type": "single",
  "confidence": 0.85,
  "is_pass": false,
  "is_bomb": false
}
```

---

### 3. 获取所有出牌建议

```bash
curl -X POST http://localhost:8000/api/actions \
  -H "Content-Type: application/json" \
  -d '{
    "position": "landlord",
    "my_cards": "568AJ2",
    "played_cards": {
      "landlord": "34",
      "landlord_up": "7",
      "landlord_down": ""
    },
    "last_moves": ["7", "5"],
    "landlord_cards": "2XD",
    "cards_left": {
      "landlord": 6,
      "landlord_up": 16,
      "landlord_down": 17
    }
  }'
```

**响应**：
```json
{
  "best_action": {
    "cards": "8",
    "win_rate": 0.85,
    "action_type": "single",
    "confidence": 0.85,
    "is_pass": false,
    "is_bomb": false
  },
  "actions": [
    {"cards": "8", "win_rate": 0.85, "action_type": "single", ...},
    {"cards": "J", "win_rate": 0.82, "action_type": "single", ...},
    ...
  ],
  "total_count": 7
}
```

---

### 4. 获取叫分建议

```bash
curl -X POST http://localhost:8000/api/bid \
  -H "Content-Type: application/json" \
  -d '{
    "cards": "345789TJQQAA22"
  }'
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `cards` | string | ✅ | 手牌 (17张) |
| `threshold` | float | ❌ | 叫分阈值 (默认 0.5) |

**响应**：
```json
{
  "should_bid": true,
  "win_rate": 0.65,
  "farmer_win_rate": 0.35,
  "confidence": 0.3
}
```

---

### 5. 获取加倍建议

```bash
curl -X POST http://localhost:8000/api/double \
  -H "Content-Type: application/json" \
  -d '{
    "cards": "345789TJQQAA22",
    "is_landlord": false,
    "landlord_cards": "3344556"
  }'
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `cards` | string | ✅ | 当前手牌 |
| `is_landlord` | bool | ✅ | 是否为地主 |
| `landlord_cards` | string | ❌ | 地主手牌 (用于比较) |
| `position` | string | ❌ | 玩家位置 (农民时) |

**响应**：
```json
{
  "should_double": true,
  "should_super_double": false,
  "win_rate": 0.65,
  "confidence": 0.3
}
```

---

## ⚡ 性能与高并发部署建议

在生产环境中，由于深度学习模型前向传播（Forward）属于 CPU/GPU 密集型运算，推荐使用以下方式部署以获得最佳的并发性能：

### 1. 启动多进程 Worker (Uvicorn)
由于 Python 的 GIL（全局解释器锁）限制，单进程无法充分利用多核 CPU。推荐通过命令行启动，并指定与机器核心数相匹配的 `workers` 数量：

```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 4
```
*注：斗地主包含3个位置的独立模型，请确保您的服务器内存/显存（RAM/VRAM）足以容纳 `workers_num * 3` 个模型副本。*

### 2. 内部优化说明
目前的 `api_server.py` 已经内置了以下高性能优化：
- **异步防阻塞 (`run_in_threadpool`)**：所有模型推理请求已放入后台线程池执行，保证 FastAPI 的异步事件循环不被阻塞，极大提升了并发吞吐量。
- **显存与速度优化 (`torch.no_grad()`)**：在推理阶段关闭了梯度计算，不仅降低了至少 50% 的显存占用，还提升了前向传播速度，防止高并发下发生 OOM (Out of Memory) 异常。

---

## 🐍 Python 调用示例

```python
import requests

# 出牌建议
response = requests.post(
    "http://localhost:8000/api/play",
    json={
        "position": "landlord",
        "my_cards": "568AJ2",
        "played_cards": {
            "landlord": "34",       # 全量累计：地主已出的所有牌
            "landlord_up": "7",     # 全量累计：上家已出的所有牌
            "landlord_down": ""     # 下家还没出过牌
        },
        "last_moves": ["7", "5"],
        "landlord_cards": "2XD",
        "cards_left": {             # 强烈建议提供
            "landlord": 6,
            "landlord_up": 16,
            "landlord_down": 17
        },
        "bomb_count": 0
    }
)

result = response.json()
print(f"建议出牌: {result['cards']}")
print(f"胜率: {result['win_rate']:.2%}")
print(f"牌型: {result['action_type']}")
```

完整示例请参考：`api_examples.py`

---

## ⚙️ 配置选项

### 配置文件（推荐）

编辑 `config.yaml` 文件配置模型：

```yaml
# 模型配置
model:
  # 模型类型: ADP 或 WP
  type: ADP
  
  # 模型基础路径
  base_path: baselines
  
  # 各位置模型路径（可选，不填则使用默认路径）
  paths:
    landlord: ""
    landlord_up: ""
    landlord_down: ""

# 服务配置
server:
  host: "0.0.0.0"
  port: 8000
  log_level: "info"
```

### 配置项说明

| 配置项 | 说明 | 默认值 |
|-------|------|--------|
| `model.type` | 模型类型 (ADP/WP) | `ADP` |
| `model.base_path` | 模型基础路径 | `baselines` |
| `model.paths.landlord` | 地主模型路径 | `{base_path}/douzero_{type}/landlord.ckpt` |
| `model.paths.landlord_up` | 地主上家模型路径 | `{base_path}/douzero_{type}/landlord_up.ckpt` |
| `model.paths.landlord_down` | 地主下家模型路径 | `{base_path}/douzero_{type}/landlord_down.ckpt` |
| `server.host` | 服务监听地址 | `0.0.0.0` |
| `server.port` | 服务端口 | `8000` |
| `server.log_level` | 日志级别 | `info` |

### 切换模型类型示例

```yaml
# 使用 WP 模型
model:
  type: WP
  base_path: baselines
```

### 使用自定义模型路径

```yaml
model:
  type: ADP
  base_path: baselines
  paths:
    landlord: /data/models/my_landlord.ckpt
    landlord_up: /data/models/my_landlord_up.ckpt
    landlord_down: /data/models/my_landlord_down.ckpt
```

---

## 🧪 测试

### 快速测试

```bash
python3 api_examples.py quick
```

### 运行完整示例

```bash
python3 api_examples.py
```

---

## 📊 性能优化建议

1. **GPU 加速**：确保 CUDA 可用以提升推理速度
2. **批量请求**：合并多个请求减少网络开销
3. **缓存机制**：对相同局面缓存结果
4. **负载均衡**：使用 Nginx 部署多实例

---

## 🔧 生产部署

### 使用 Systemd

创建 `/etc/systemd/system/douzero-api.service`：

```ini
[Unit]
Description=DouZero API Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/DouZero
ExecStart=/path/to/python3 api_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl start douzero-api
sudo systemctl enable douzero-api
```

### 使用 Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements_api.txt

EXPOSE 8000

CMD ["python3", "api_server.py"]
```

构建运行：

```bash
docker build -t douzero-api .
docker run -p 8000:8000 douzero-api
```

使用自定义配置文件：

```bash
# 挂载本地配置文件
docker run -p 8000:8000 -v /path/to/config.yaml:/app/config.yaml douzero-api
```

---

## 📝 注意事项

1. **首次启动**：模型加载需要 10-30 秒
2. **内存占用**：每个模型约 20MB，三个模型共 60MB
3. **并发处理**：FastAPI 自动支持异步，无需额外配置
4. **CORS**：已允许所有来源访问，生产环境建议限制

---

## 🐛 常见问题

### Q: 启动失败 "模型未找到"

```bash
# 确保预训练模型存在
ls baselines/douzero_ADP/
```

### Q: 推理速度慢

检查 GPU 是否可用：
```bash
python3 -c "import torch; print(torch.cuda.is_available())"
```

### Q: 接口返回 500 错误

查看服务器日志，通常是由于：
- 手牌格式错误（确保使用字符串格式如 "3456789TJQKA2XD"）
- 位置参数无效
- last_moves 格式错误

---

## 📞 技术支持

- GitHub Issues: [https://github.com/kwai/DouZero/issues](https://github.com/kwai/DouZero/issues)
- 论文: [https://arxiv.org/abs/2106.06135](https://arxiv.org/abs/2106.06135)
