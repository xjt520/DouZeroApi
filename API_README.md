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
| `/api/deal` | GET | 随机发牌模拟开局 |
| `/api/act` | POST | 获取出牌建议 |
| `/api/bid` | POST | 获取叫分建议 |
| `/api/double` | POST | 获取加倍建议 |
| `/test_api.html` | GET | API测试页面 |
| `/docs` | GET | Swagger API 文档 |

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
  "gpu_available": true,
  "models_loaded": true,
  "model_config": {
    "model_type": "ADP",
    "model_base_path": "baselines",
    "model_paths": {
      "landlord": "baselines/douzero_ADP/landlord.ckpt",
      "landlord_up": "baselines/douzero_ADP/landlord_up.ckpt",
      "landlord_down": "baselines/douzero_ADP/landlord_down.ckpt"
    }
  }
}
```

---

### 2. 随机发牌

```bash
curl http://localhost:8000/api/deal
```

**响应**：
```json
{
  "landlord": [30, 20, 17, 17, 14, 13, 13, 11, 10, 9, 8, 8, 7, 6, 6, 5, 4, 4, 3, 3],
  "landlord_up": [17, 14, 14, 13, 12, 12, 11, 10, 9, 9, 8, 7, 7, 6, 5, 4, 3],
  "landlord_down": [17, 14, 13, 12, 12, 11, 11, 10, 10, 9, 8, 7, 6, 5, 5, 4, 3],
  "three_landlord_cards": [17, 14, 13]
}
```

---

### 3. 获取出牌建议

```bash
curl -X POST http://localhost:8000/api/act \
  -H "Content-Type: application/json" \
  -d '{
    "position": "landlord",
    "player_hand_cards": [5, 6, 8, 11, 14, 17],
    "card_play_action_seq": [[], [3], [], [5]],
    "three_landlord_cards": [17, 20, 30],
    "bomb_num": 0
  }'
```

**请求参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `position` | string | ✅ | 玩家位置: `landlord`, `landlord_up`, `landlord_down` |
| `player_hand_cards` | array | ✅ | 玩家手牌 |
| `card_play_action_seq` | array | ✅ | 历史出牌序列 |
| `three_landlord_cards` | array | ❌ | 地主底牌 |
| `bomb_num` | int | ❌ | 已出炸弹数量 |

**响应**：
```json
{
  "action": [8],
  "action_str": "8",
  "confidence": 0.85,
  "legal_actions": [[5], [6], [8], [11], [14], [17], []],
  "model_used": "douzero_ADP_landlord"
}
```

> 注：`model_used` 字段显示实际使用的模型类型和位置，可通过环境变量 `DOUZERO_MODEL_TYPE` 切换。

---

### 4. 获取叫分建议 (基于 Q-Value)

```bash
curl -X POST http://localhost:8000/api/bid \
  -H "Content-Type: application/json" \
  -d '{
    "position": "landlord_up",
    "hand_cards": [3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 14, 17, 17],
    "three_landlord_cards": [17, 20, 30]
  }'
```

**响应**：
```json
{
  "bid": 3,
  "bid_reason": "模型预测胜率极高，叫3分抢地主 (Q-Value: 0.65)"
}
```

---

### 5. 获取加倍建议 (基于 Q-Value)

```bash
curl -X POST http://localhost:8000/api/double \
  -H "Content-Type: application/json" \
  -d '{
    "position": "landlord_up",
    "hand_cards": [3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 14, 17, 17],
    "current_landlord_score": 2,
    "landlord_cards": []
  }'
```

**响应**：
```json
{
  "double": true,
  "double_reason": "手牌价值明显强于地主，建议加倍 (己方: 0.65, 地主: 0.05)"
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
    "http://localhost:8000/api/act",
    json={
        "position": "landlord",
        "player_hand_cards": [5, 6, 8, 11, 14, 17],
        "card_play_action_seq": [[], [3], [], [5]],
        "three_landlord_cards": [17, 20, 30],
        "bomb_num": 0
    }
)

result = response.json()
print(f"建议出牌: {result['action_str']}")
print(f"置信度: {result['confidence']:.2%}")
```

完整示例请参考：`api_examples.py`

---

## 🎴 牌值映射表

| 数值 | 牌面 |
|------|------|
| 3-14 | 3-A |
| 17 | 2 |
| 20 | 小王 (X) |
| 30 | 大王 (D) |

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

### 查看当前配置

启动后访问 `/api/config` 端点：

```bash
curl http://localhost:8000/api/config
```

响应示例：
```json
{
  "model_type": "ADP",
  "model_base_path": "baselines",
  "model_paths": {
    "landlord": "baselines/douzero_ADP/landlord.ckpt",
    "landlord_up": "baselines/douzero_ADP/landlord_up.ckpt",
    "landlord_down": "baselines/douzero_ADP/landlord_down.ckpt"
  },
  "available_model_types": ["ADP", "WP"],
  "config_file": "config.yaml"
}
```

### 修改端口

编辑 `api_server.py` 底部：

```python
uvicorn.run(app, host="0.0.0.0", port=8080)  # 改为 8080
```

---

## 🧪 测试

### 测试页面

启动服务后，在浏览器访问：

```
http://localhost:8000/test_api.html
```

测试页面功能：
- ✅ 健康检查
- ✅ 查看模型配置
- ✅ 出牌建议测试（含快速填充示例）
- ✅ 叫分建议测试
- ✅ 加倍建议测试

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
- 手牌格式错误
- 位置参数无效
- 历史序列格式错误

---

## 📞 技术支持

- GitHub Issues: [https://github.com/kwai/DouZero/issues](https://github.com/kwai/DouZero/issues)
- 论文: [https://arxiv.org/abs/2106.06135](https://arxiv.org/abs/2106.06135)
