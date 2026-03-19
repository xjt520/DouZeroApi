"""
DouZero REST API Service
基于 FastAPI 的斗地主 AI 接口服务
"""

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional
import torch
import numpy as np
from collections import Counter
import os
import yaml

# 导入 DouZero 模块
from douzero.env.game import GameEnv
from douzero.evaluation.deep_agent import DeepAgent
from douzero.env.move_generator import MovesGener
from douzero.env import move_detector as md

# ============ 配置管理 ============

class Config:
    """配置类 - 从 config.yaml 读取配置"""
    
    _config: Dict = {}
    _loaded: bool = False
    
    @classmethod
    def load(cls, config_path: str = "config.yaml"):
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._config = yaml.safe_load(f)
            cls._loaded = True
            print(f"✅ 配置文件加载成功: {config_path}")
        except FileNotFoundError:
            print(f"⚠️  配置文件未找到: {config_path}，使用默认配置")
            cls._config = cls._get_default_config()
            cls._loaded = True
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}，使用默认配置")
            cls._config = cls._get_default_config()
            cls._loaded = True
    
    @classmethod
    def _get_default_config(cls) -> Dict:
        """获取默认配置"""
        return {
            "model": {
                "type": "ADP",
                "base_path": "baselines",
                "paths": {
                    "landlord": "",
                    "landlord_up": "",
                    "landlord_down": ""
                }
            },
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "log_level": "info"
            }
        }
    
    @classmethod
    def get(cls, key: str, default=None):
        """获取配置值（支持点分隔的嵌套键）"""
        if not cls._loaded:
            cls.load()
        
        keys = key.split('.')
        value = cls._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    @classmethod
    @property
    def MODEL_TYPE(cls) -> str:
        return cls.get('model.type', 'ADP')
    
    @classmethod
    @property
    def MODEL_BASE_PATH(cls) -> str:
        return cls.get('model.base_path', 'baselines')
    
    @classmethod
    @property
    def SERVER_HOST(cls) -> str:
        return cls.get('server.host', '0.0.0.0')
    
    @classmethod
    @property
    def SERVER_PORT(cls) -> int:
        return cls.get('server.port', 8000)
    
    @classmethod
    @property
    def SERVER_LOG_LEVEL(cls) -> str:
        return cls.get('server.log_level', 'info')
    
    @classmethod
    def get_model_paths(cls) -> Dict[str, str]:
        """获取模型路径配置"""
        model_dir = f"douzero_{cls.MODEL_TYPE}"
        base_path = cls.MODEL_BASE_PATH
        
        # 从配置文件读取各位置路径
        landlord_path = cls.get('model.paths.landlord', '')
        landlord_up_path = cls.get('model.paths.landlord_up', '')
        landlord_down_path = cls.get('model.paths.landlord_down', '')
        
        # 优先使用配置的路径，否则使用默认路径
        paths = {
            'landlord': landlord_path or os.path.join(base_path, model_dir, 'landlord.ckpt'),
            'landlord_up': landlord_up_path or os.path.join(base_path, model_dir, 'landlord_up.ckpt'),
            'landlord_down': landlord_down_path or os.path.join(base_path, model_dir, 'landlord_down.ckpt'),
        }
        return paths
    
    @classmethod
    def get_model_info(cls) -> Dict[str, str]:
        """获取模型配置信息"""
        return {
            "model_type": cls.MODEL_TYPE,
            "model_base_path": cls.MODEL_BASE_PATH,
            "model_paths": cls.get_model_paths()
        }
    
    @classmethod
    def get_full_config(cls) -> Dict:
        """获取完整配置"""
        if not cls._loaded:
            cls.load()
        return cls._config

# ============ FastAPI 应用 ============
app = FastAPI(
    title="DouZero API",
    description="斗地主 AI 接口服务 - 基于 DouZero 深度强化学习模型",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 数据模型 ============

class ActRequest(BaseModel):
    """出牌建议请求 - 支持模型所有入参"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "position": "landlord",
                "player_hand_cards": [5, 6, 8, 11, 14, 17],
                "card_play_action_seq": [[], [3], [], [5]],
                "three_landlord_cards": [17, 20, 30],
                "bomb_num": 0,
                "num_cards_left_dict": {"landlord": 17, "landlord_up": 17, "landlord_down": 17},
                "other_hand_cards": [3, 4, 7, 9, 10, 12, 13, 15, 16, 18, 19, 20, 30],
                "last_move": [5],
                "last_two_moves": [[3], [5]],
                "last_move_dict": {"landlord": [5], "landlord_up": [], "landlord_down": [3]},
                "played_cards": {"landlord": [5], "landlord_up": [], "landlord_down": [3]},
                "last_pid": "landlord_down"
            }
        }
    )
    position: str = Field(..., description="玩家位置: landlord, landlord_up, landlord_down")
    player_hand_cards: List[int] = Field(..., description="玩家手牌，如 [3,3,5,6,8,11,14,17]")
    card_play_action_seq: List[List[int]] = Field(default=[], description="历史出牌序列")
    three_landlord_cards: List[int] = Field(default=[], description="地主底牌（可选）")
    bomb_num: int = Field(default=0, description="已出炸弹数量")
    num_cards_left_dict: Optional[Dict[str, int]] = Field(default=None, description="各玩家剩余牌数")
    other_hand_cards: Optional[List[int]] = Field(default=None, description="其他玩家手牌（联合）")
    last_move: Optional[List[int]] = Field(default=None, description="最近一次有效出牌")
    last_two_moves: Optional[List[List[int]]] = Field(default=None, description="最近两次出牌")
    last_move_dict: Optional[Dict[str, List[int]]] = Field(default=None, description="各位置最后出牌")
    played_cards: Optional[Dict[str, List[int]]] = Field(default=None, description="各位置已出的牌")
    last_pid: Optional[str] = Field(default=None, description="最后出牌玩家位置")

class ActResponse(BaseModel):
    """出牌建议响应"""
    action: List[int] = Field(..., description="建议出牌，空列表 [] 表示过牌")
    action_str: str = Field(..., description="出牌的字符串表示")
    confidence: float = Field(..., description="置信度 (0-1)")
    legal_actions: List[List[int]] = Field(..., description="所有合法出牌")
    model_used: str = Field(..., description="使用的模型")

class BidRequest(BaseModel):
    """叫分建议请求"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "position": "landlord_up",
                "hand_cards": [3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 14, 17, 17],
                "three_landlord_cards": [17, 20, 30]
            }
        }
    )
    position: str = Field(..., description="玩家位置: landlord, landlord_up, landlord_down")
    hand_cards: List[int] = Field(..., description="手牌")
    three_landlord_cards: List[int] = Field(default=[], description="底牌（可选）")

class BidResponse(BaseModel):
    """叫分建议响应"""
    bid: int = Field(..., description="建议叫分: 0, 1, 2, 3")
    bid_reason: str = Field(..., description="叫分原因")

class DoubleRequest(BaseModel):
    """加倍建议请求"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "position": "landlord_up",
                "hand_cards": [3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 14, 17, 17],
                "current_landlord_score": 3,
                "landlord_cards": []
            }
        }
    )
    position: str = Field(..., description="玩家位置: landlord, landlord_up, landlord_down")
    hand_cards: List[int] = Field(..., description="手牌")
    current_landlord_score: int = Field(..., description="当前地主叫分")
    landlord_cards: List[int] = Field(default=[], description="地主手牌（如果已知）")

class DoubleResponse(BaseModel):
    """加倍建议响应"""
    double: bool = Field(..., description="是否加倍")
    double_reason: str = Field(..., description="加倍原因")

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    gpu_available: bool
    models_loaded: bool
    model_info: Dict = Field(..., description="模型配置信息")

# ============ 全局模型管理 ============

class ModelManager:
    """模型管理器"""
    def __init__(self):
        self.models = {}
        self.loaded = False
        self.model_paths = {}

    def load_models(self, model_paths: Dict[str, str] = None):
        """加载模型"""
        if model_paths is None:
            model_paths = Config.get_model_paths()
        
        self.model_paths = model_paths

        try:
            for position, path in model_paths.items():
                self.models[position] = DeepAgent(position, path)
            self.loaded = True
            print(f"✅ 模型加载成功 (类型: {Config.MODEL_TYPE})")
            for pos, path in model_paths.items():
                print(f"   - {pos}: {path}")
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            self.loaded = False

    def get_model(self, position: str) -> DeepAgent:
        """获取指定位置的模型"""
        if not self.loaded:
            raise HTTPException(status_code=503, detail="模型未加载")
        if position not in self.models:
            raise HTTPException(status_code=400, detail=f"无效的位置: {position}")
        return self.models[position]

# 全局模型管理器实例
model_manager = ModelManager()

# ============ 辅助函数 ============

def cards_to_string(cards: List[int]) -> str:
    """将牌值列表转换为字符串"""
    card_map = {
        3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9', 10: '10',
        11: 'J', 12: 'Q', 13: 'K', 14: 'A', 17: '2', 20: '小王', 30: '大王'
    }
    if not cards:
        return "过"
    return ' '.join(card_map.get(c, str(c)) for c in cards)

def calculate_hand_strength(cards: List[int]) -> float:
    """计算手牌强度 (0-1)"""
    if not cards:
        return 0.0

    counter = Counter(cards)
    score = 0.0

    # 大牌权重
    for card, count in counter.items():
        if card == 30:  # 大王
            score += 0.08 * count
        elif card == 20:  # 小王
            score += 0.06 * count
        elif card == 17:  # 2
            score += 0.04 * count
        elif card == 14:  # A
            score += 0.03 * count
        elif card == 13:  # K
            score += 0.02 * count
        elif card == 12:  # Q
            score += 0.015 * count
        elif card == 11:  # J
            score += 0.01 * count

    # 炸弹加分
    for card, count in counter.items():
        if count == 4:
            score += 0.1
        if (card == 20 or card == 30) and count >= 1:
            score += 0.05

    return min(score, 1.0)

def predict_hand_value(hand_cards: List[int], three_landlord_cards: List[int] = None) -> float:
    """利用 DouZero 模型估算手牌价值 (Q-Value)"""
    from douzero.env.game import InfoSet
    from douzero.env.env import get_obs
    
    # 叫地主阶段如果没有拿到三张底牌，我们通常扮演 landlord_up 评估（17张）
    # 如果已经合并了三张底牌，那就扮演 landlord 评估（20张）
    total_cards = len(hand_cards) + (len(three_landlord_cards) if three_landlord_cards else 0)
    position = 'landlord' if total_cards >= 20 else 'landlord_up'
    
    try:
        agent = model_manager.get_model(position)
    except Exception:
        return (calculate_hand_strength(hand_cards) - 0.5) * 2
    
    full_hand = hand_cards.copy()
    if three_landlord_cards and position == 'landlord':
        full_hand.extend(three_landlord_cards)
        
    infoset = InfoSet(position)
    infoset.player_hand_cards = full_hand
    
    # 生成作为第一个出牌人的合法动作
    mg = MovesGener(full_hand)
    legal_actions = mg.gen_moves()
    if not legal_actions:
        legal_actions = [[]]
        
    infoset.legal_actions = legal_actions
    infoset.last_move = []
    infoset.last_two_moves = [[], []]
    infoset.last_pid = 'landlord'
    infoset.played_cards = {'landlord': [], 'landlord_up': [], 'landlord_down': []}
    infoset.last_move_dict = {'landlord': [], 'landlord_up': [], 'landlord_down': []}
    infoset.bomb_num = 0
    infoset.other_hand_cards = []
    
    if position == 'landlord':
        infoset.num_cards_left_dict = {
            'landlord': len(full_hand),
            'landlord_up': 17,
            'landlord_down': 17
        }
    else:
        infoset.num_cards_left_dict = {
            'landlord': 20,
            'landlord_up': len(full_hand),
            'landlord_down': 17
        }
        
    infoset.card_play_action_seq = []
    infoset.three_landlord_cards = three_landlord_cards or []
    
    try:
        obs = get_obs(infoset)
        z_batch = torch.from_numpy(obs['z_batch']).float()
        x_batch = torch.from_numpy(obs['x_batch']).float()
        if torch.cuda.is_available():
            z_batch, x_batch = z_batch.cuda(), x_batch.cuda()
            
        with torch.no_grad():
            y_pred = agent.model.forward(z_batch, x_batch, return_value=True)['values']
        y_pred = y_pred.detach().cpu().numpy()
        
        # 返回所有动作中最大的Q-value（胜率期望），范围通常在 -1 到 1 之间
        return float(np.max(y_pred))
    except Exception as e:
        print(f"模型预测失败，使用启发式回退: {e}")
        # 回退：将 0-1 映射回大致的 -1 到 1 区间
        return (calculate_hand_strength(full_hand) - 0.5) * 2

def get_legal_actions_from_cards(hand_cards: List[int], last_move: List[int]) -> List[List[int]]:
    """从手牌获取合法出牌"""
    mg = MovesGener(hand_cards)

    if not last_move:
        return mg.gen_moves()

    rival_type = md.get_move_type(last_move)
    rival_move_type = rival_type['type']
    rival_move_len = rival_type.get('len', 1)

    if rival_move_type == md.TYPE_0_PASS:
        return mg.gen_moves()
    elif rival_move_type == md.TYPE_1_SINGLE:
        return mg.gen_type_1_single()
    elif rival_move_type == md.TYPE_2_PAIR:
        return mg.gen_type_2_pair()
    elif rival_move_type == md.TYPE_3_TRIPLE:
        return mg.gen_type_3_triple()
    elif rival_move_type == md.TYPE_4_TRIPLE_WITH_ONE:
        return mg.gen_type_4_triple_with_one()
    elif rival_move_type == md.TYPE_5_TRIPLE_WITH_TWO:
        return mg.gen_type_5_triple_with_two()
    elif rival_move_type == md.TYPE_6_FOUR_WITH_TWO:
        return mg.gen_type_6_four_with_two()
    elif rival_move_type == md.TYPE_7_STRAIGHT:
        return mg.gen_type_7_straight(rival_move_len)
    elif rival_move_type == md.TYPE_8_STRAIGHT_PAIR:
        return mg.gen_type_8_straight_pair(rival_move_len)
    elif rival_move_type == md.TYPE_9_PLANE_WITH_ONE:
        return mg.gen_type_9_plane_with_one(rival_move_len)
    elif rival_move_type == md.TYPE_10_PLANE_WITH_TWO:
        return mg.gen_type_10_plane_with_two(rival_move_len)
    elif rival_move_type == md.TYPE_11_BOMB:
        return mg.gen_type_11_bomb()
    elif rival_move_type == md.TYPE_12_ROCKET:
        return []  # 王炸无法压制

    return []

# ============ API 端点 ============

@app.on_event("startup")
async def startup_event():
    """服务启动时加载模型"""
    print("🚀 DouZero API 服务启动中...")
    Config.load()
    print(f"📦 模型类型: {Config.MODEL_TYPE}")
    print(f"📦 模型基础路径: {Config.MODEL_BASE_PATH}")
    print("📦 正在加载模型...")
    model_manager.load_models()
    print("✅ 服务启动完成！")

@app.get("/", summary="根路径")
async def root():
    """根路径，返回服务信息"""
    return {
        "service": "DouZero API",
        "version": "1.0.0",
        "status": "running",
        "model_type": Config.MODEL_TYPE,
        "endpoints": {
            "health": "/api/health",
            "config": "/api/config",
            "act": "/api/act",
            "bid": "/api/bid",
            "double": "/api/double",
            "test_page": "/test_api.html",
            "docs": "/docs"
        }
    }

@app.get("/test_api.html", response_class=HTMLResponse, summary="API测试页面")
async def test_page():
    """返回API测试页面"""
    try:
        with open("test_api.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="测试页面未找到")

@app.get("/api/config", summary="获取模型配置")
async def get_config():
    """获取当前模型配置信息"""
    return {
        "model_type": Config.MODEL_TYPE,
        "model_base_path": Config.MODEL_BASE_PATH,
        "model_paths": model_manager.model_paths if model_manager.loaded else Config.get_model_paths(),
        "available_model_types": ["ADP", "WP"],
        "config_file": "config.yaml",
        "full_config": Config.get_full_config()
    }

@app.get("/api/health", response_model=HealthResponse, summary="健康检查")
async def health_check():
    """检查服务健康状态"""
    return HealthResponse(
        status="healthy" if model_manager.loaded else "unhealthy",
        gpu_available=torch.cuda.is_available(),
        models_loaded=model_manager.loaded,
        model_info=Config.get_model_info()
    )

class DealResponse(BaseModel):
    landlord: List[int] = Field(..., description="地主手牌（带底牌），共 20 张")
    landlord_up: List[int] = Field(..., description="地主上家手牌，共 17 张")
    landlord_down: List[int] = Field(..., description="地主下家手牌，共 17 张")
    three_landlord_cards: List[int] = Field(..., description="三张底牌")

@app.get("/api/deal", response_model=DealResponse, summary="随机发牌")
async def get_deal():
    """
    随机洗牌并分配卡牌，模拟真实开局

    返回三个位置的初始手牌和三张底牌。默认将三张底牌分配给 landlord。
    """
    try:
        # 生成一副完整的 54 张牌
        deck = []
        for i in range(3, 15):
            deck.extend([i for _ in range(4)])
        deck.extend([17 for _ in range(4)])
        deck.extend([20, 30])

        # 随机洗牌
        np.random.shuffle(deck)

        # 按照规则发牌
        landlord_cards = deck[:20]
        landlord_up_cards = deck[20:37]
        landlord_down_cards = deck[37:54]
        three_landlord_cards = deck[17:20]

        # 为手牌排序
        landlord_cards.sort(reverse=True)
        landlord_up_cards.sort(reverse=True)
        landlord_down_cards.sort(reverse=True)
        three_landlord_cards.sort(reverse=True)

        return DealResponse(
            landlord=landlord_cards,
            landlord_up=landlord_up_cards,
            landlord_down=landlord_down_cards,
            three_landlord_cards=three_landlord_cards
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发牌失败: {str(e)}")

@app.post("/api/act", response_model=ActResponse, summary="获取出牌建议")
async def get_action(request: ActRequest):
    """
    获取出牌建议 - 支持模型所有入参

    必需参数:
    - **position**: 玩家位置 (landlord, landlord_up, landlord_down)
    - **player_hand_cards**: 玩家手牌

    可选参数（提供完整参数可提高模型准确性）:
    - **card_play_action_seq**: 历史出牌序列
    - **three_landlord_cards**: 地主底牌
    - **bomb_num**: 已出炸弹数量
    - **num_cards_left_dict**: 各玩家剩余牌数 {"landlord": int, "landlord_up": int, "landlord_down": int}
    - **other_hand_cards**: 其他玩家手牌（联合）
    - **last_move**: 最近一次有效出牌
    - **last_two_moves**: 最近两次出牌
    - **last_move_dict**: 各位置最后出牌 {"landlord": [], "landlord_up": [], "landlord_down": []}
    - **played_cards**: 各位置已出的牌 {"landlord": [], "landlord_up": [], "landlord_down": []}
    - **last_pid**: 最后出牌玩家位置

    返回建议的出牌动作
    """
    try:
        # 获取模型
        agent = model_manager.get_model(request.position)

        # 获取最近一次出牌
        if request.card_play_action_seq:
            if len(request.card_play_action_seq[-1]) == 0:
                last_move = request.card_play_action_seq[-2] if len(request.card_play_action_seq) >= 2 else []
            else:
                last_move = request.card_play_action_seq[-1]
        else:
            last_move = []

        # 获取合法动作
        try:
            legal_actions = get_legal_actions_from_cards(request.player_hand_cards, last_move)
            if not legal_actions:
                legal_actions = [[]]  # 只能过
        except Exception as e:
            # 如果生成合法动作失败，返回过牌
            legal_actions = [[]]

        # 构造游戏状态
        from douzero.env.game import InfoSet
        infoset = InfoSet(request.position)
        infoset.player_hand_cards = request.player_hand_cards
        infoset.card_play_action_seq = request.card_play_action_seq
        infoset.three_landlord_cards = request.three_landlord_cards
        infoset.bomb_num = request.bomb_num
        infoset.legal_actions = legal_actions
        infoset.last_move = request.last_move if request.last_move is not None else last_move

        # 必需字段 - 优先使用请求参数，否则使用默认值
        if request.num_cards_left_dict is not None:
            infoset.num_cards_left_dict = request.num_cards_left_dict
        else:
            infoset.num_cards_left_dict = {
                'landlord': len(request.player_hand_cards) if request.position == 'landlord' else 17,
                'landlord_up': len(request.player_hand_cards) if request.position == 'landlord_up' else 17,
                'landlord_down': len(request.player_hand_cards) if request.position == 'landlord_down' else 17
            }

        if request.other_hand_cards is not None:
            infoset.other_hand_cards = request.other_hand_cards
        else:
            infoset.other_hand_cards = []

        if request.played_cards is not None:
            infoset.played_cards = request.played_cards
        else:
            infoset.played_cards = {'landlord': [], 'landlord_up': [], 'landlord_down': []}

        if request.last_move_dict is not None:
            infoset.last_move_dict = request.last_move_dict
        else:
            infoset.last_move_dict = {'landlord': [], 'landlord_up': [], 'landlord_down': []}

        if request.last_two_moves is not None:
            infoset.last_two_moves = request.last_two_moves
        else:
            infoset.last_two_moves = [[], []]

        infoset.all_handcards = {
            'landlord': request.player_hand_cards if request.position == 'landlord' else [],
            'landlord_up': request.player_hand_cards if request.position == 'landlord_up' else [],
            'landlord_down': request.player_hand_cards if request.position == 'landlord_down' else []
        }

        if request.last_pid is not None:
            infoset.last_pid = request.last_pid
        else:
            infoset.last_pid = 'landlord'

        # 模型推理
        if len(legal_actions) == 1:
            # 只有一个合法动作，直接返回
            action = legal_actions[0]
            confidence = 1.0
        else:
            action = await run_in_threadpool(agent.act, infoset)
            # 简单置信度计算（实际可以改进）
            confidence = 0.85

        return ActResponse(
            action=action,
            action_str=cards_to_string(action),
            confidence=confidence,
            legal_actions=legal_actions,
            model_used=f"douzero_{Config.MODEL_TYPE}_{request.position}"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"出牌建议生成失败: {str(e)}")

@app.post("/api/bid", response_model=BidResponse, summary="获取叫分建议")
async def get_bid(request: BidRequest):
    """
    获取叫分建议

    基于 DouZero 模型价值网络 (Q-Value) 预测的胜率进行叫分
    """
    try:
        # 初始估算强度 (预期胜率，范围大约在 -1 到 1)
        strength = await run_in_threadpool(predict_hand_value, request.hand_cards)

        # 如果有底牌，计算加上底牌后的强度
        final_strength = strength
        if request.three_landlord_cards:
            final_strength = await run_in_threadpool(predict_hand_value, request.hand_cards, request.three_landlord_cards)

        # 根据模型胜率预测决定叫分
        if final_strength >= 0.4:
            bid = 3
            reason = "模型预测胜率极高，叫3分抢地主"
        elif final_strength >= 0.1:
            bid = 2
            reason = "模型预测胜率较高，叫2分"
        elif final_strength >= -0.2:
            bid = 1
            reason = "模型预测有一定的胜率，叫1分"
        else:
            bid = 0
            reason = "模型预测胜率较低，不叫"

        return BidResponse(bid=bid, bid_reason=f"{reason} (Q-Value: {final_strength:.2f})")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"叫分建议生成失败: {str(e)}")

@app.post("/api/double", response_model=DoubleResponse, summary="获取加倍建议")
async def get_double(request: DoubleRequest):
    """
    获取加倍建议

    基于 DouZero 模型价值网络的策略
    """
    try:
        strength = await run_in_threadpool(predict_hand_value, request.hand_cards)

        # 如果知道地主手牌，考虑对手强度
        opponent_strength = 0.0
        if request.landlord_cards:
            # 传空底牌，因为 landlord_cards 应该已经是20张
            opponent_strength = await run_in_threadpool(predict_hand_value, request.landlord_cards)

        # 决策逻辑
        if request.position == 'landlord':
            # 地主不加倍
            return DoubleResponse(
                double=False,
                double_reason=f"地主不参与加倍 (己方 Q-Value: {strength:.2f})"
            )
        else:
            # 农民决定是否加倍
            if strength > opponent_strength + 0.3 and request.current_landlord_score <= 2:
                double = True
                reason = f"手牌价值明显强于地主，建议加倍 (己方: {strength:.2f}, 地主: {opponent_strength:.2f})"
            elif strength >= 0.2 and request.current_landlord_score == 1:
                double = True
                reason = f"手牌胜率较高且地主叫分较低，建议加倍 (己方: {strength:.2f})"
            else:
                double = False
                reason = f"不建议加倍 (己方: {strength:.2f}, 地主: {opponent_strength:.2f})"

            return DoubleResponse(double=double, double_reason=reason)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加倍建议生成失败: {str(e)}")

# ============ 启动命令 ============

if __name__ == "__main__":
    import uvicorn
    
    Config.load()
    
    print("=" * 50)
    print("🎮 DouZero API 服务")
    print("=" * 50)
    print(f"📦 模型类型: {Config.MODEL_TYPE}")
    print(f"📖 API 文档: http://localhost:{Config.SERVER_PORT}/docs")
    print(f"🔍 健康检查: http://localhost:{Config.SERVER_PORT}/api/health")
    print(f"⚙️  模型配置: http://localhost:{Config.SERVER_PORT}/api/config")
    print("=" * 50)
    print("💡 配置文件: config.yaml")
    print("   model.type: ADP | WP")
    print("   model.base_path: baselines")
    print("   model.paths.landlord: /path/to/landlord.ckpt")
    print("=" * 50)

    uvicorn.run(
        app,
        host=Config.SERVER_HOST,
        port=Config.SERVER_PORT,
        log_level=Config.SERVER_LOG_LEVEL
    )
