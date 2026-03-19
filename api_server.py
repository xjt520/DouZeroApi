import logging
from typing import List, Dict, Optional
import os
import yaml
import copy
import numpy as np

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import torch
import uvicorn

# Imports from DouZeroApi
from douzero.evaluation.deep_agent import DeepAgent

# Local imports
from api.models import (
    PlayRequest, ActionResponse, ActionsResponse,
    BidRequest, BidResponse, DoubleRequest, DoubleResponse, HealthResponse
)
from api.utils import CardConverter, ActionTypeDetector
from api.services import DouZeroService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ Console Logging Helpers ============
_POS_CN = {
    "landlord":      "地主",
    "landlord_up":   "农民(上家)",
    "landlord_down": "农民(下家)",
}
_WIN_BAR_WIDTH = 20

def _win_bar(rate: float) -> str:
    clamped = max(0.0, min(1.0, rate))
    filled = round(clamped * _WIN_BAR_WIDTH)
    bar = "█" * filled + "░" * (_WIN_BAR_WIDTH - filled)
    return f"{bar}  {rate * 100:.1f}%"

def _log_play(request: PlayRequest, result: ActionResponse) -> None:
    pos = request.position
    played = request.played_cards or {}
    cards_left = request.cards_left or {}

    def fmt_played(p: str) -> str:
        v = played.get(p, "")
        return v if v else "（无）"

    def fmt_left(p: str) -> str:
        v = cards_left.get(p)
        return f"{v} 张" if v is not None else "未知"

    last = "、".join(f"[{m}]" for m in request.last_moves) if request.last_moves else "（无）"
    rec = "[不出]" if not result.cards else result.cards

    bomb_str = f"{request.bomb_count} 个" if request.bomb_count else "0 个"
    bid_str = "有" if request.bid_info else "无"
    mul_str = "有" if request.multiply_info else "无"

    lines = [
        "",
        "┌──────────────────────────────────────────────────────┐",
        f"│  🃏  出牌建议  [{_POS_CN.get(pos, pos)}]",
        "├─────────────┬────────────────────────────────────────┤",
        f"│  我的手牌   │  {request.my_cards}  ({len(request.my_cards)} 张)",
        f"│  底牌       │  {request.landlord_cards if request.landlord_cards else '（未知）'}",
        "├─────────────┼────────────────────────────────────────┤",
        f"│  地主出牌   │  {fmt_played('landlord')}",
        f"│  上家出牌   │  {fmt_played('landlord_up')}",
        f"│  下家出牌   │  {fmt_played('landlord_down')}",
        "├─────────────┼────────────────────────────────────────┤",
        f"│  最近出牌   │  {last}",
        "├─────────────┼────────────────────────────────────────┤",
        f"│  地主剩余   │  {fmt_left('landlord')}",
        f"│  上家剩余   │  {fmt_left('landlord_up')}",
        f"│  下家剩余   │  {fmt_left('landlord_down')}",
        "├─────────────┼────────────────────────────────────────┤",
        f"│  炸弹数量   │  {bomb_str}",
        f"│  叫分信息   │  {bid_str}",
        f"│  加倍信息   │  {mul_str}",
        "├─────────────┼────────────────────────────────────────┤",
        f"│  推荐出牌   │  {rec}  ({result.action_type})",
        f"│  胜率       │  {_win_bar(result.win_rate)}",
        "└─────────────┴────────────────────────────────────────┘",
    ]
    logger.info("\n".join(lines))

def _log_actions(pos: str, my_cards: str, result: ActionsResponse) -> None:
    header = (
        "\n"
        "┌─────────────────────────────────────────────────────┐\n"
        f"│  🃏  全量出牌  [{_POS_CN.get(pos, pos)}]  手牌: {my_cards}\n"
        "├────┬────────────────┬──────────────┬────────────────┤\n"
        "│ #  │ 出牌           │ 类型         │ 胜率           │\n"
        "├────┼────────────────┼──────────────┼────────────────┤"
    )
    rows = []
    for i, a in enumerate(result.actions[:10], 1):
        mark = "★" if a.cards == result.best_action.cards else " "
        cards_str = "[不出]" if not a.cards else a.cards
        rows.append(
            f"│{mark}{i:<2} │ {cards_str:<14} │ {a.action_type:<12} │ {a.win_rate * 100:>5.1f}%          │"
        )
    footer = "└────┴────────────────┴──────────────┴────────────────┘"
    logger.info("\n".join([header] + rows + [footer]))

def _log_bid(cards: str, result: BidResponse) -> None:
    decision = "✅ 叫地主" if result.should_bid else "❌ 不叫"
    lines = [
        "",
        "┌─────────────────────────────────────────┐",
        "│  🎯  叫地主评估",
        "├──────────────┬──────────────────────────┤",
        f"│  手牌        │  {cards}",
        f"│  建议        │  {decision}",
        f"│  叫地主胜率  │  {_win_bar(result.win_rate)}",
        f"│  当农民胜率  │  {_win_bar(result.farmer_win_rate)}",
        "└──────────────┴──────────────────────────┘",
    ]
    logger.info("\n".join(lines))

def _log_double(cards: str, is_landlord: bool, result: DoubleResponse) -> None:
    role = "地主" if is_landlord else "农民"
    if result.should_super_double:
        decision = "🔥 超级加倍"
    elif result.should_double:
        decision = "⚡ 加倍"
    else:
        decision = "➖ 不加倍"
    lines = [
        "",
        "┌─────────────────────────────────────────┐",
        f"│  💰  加倍评估  [{role}]",
        "├──────────────┬──────────────────────────┤",
        f"│  手牌        │  {cards}",
        f"│  建议        │  {decision}",
        f"│  胜率        │  {_win_bar(result.win_rate)}",
        "└──────────────┴──────────────────────────┘",
    ]
    logger.info("\n".join(lines))


# ============ Model Management ============
class Config:
    _config: Dict = {}
    _loaded: bool = False
    
    @classmethod
    def load(cls, config_path: str = "config.yaml"):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._config = yaml.safe_load(f)
            cls._loaded = True
        except Exception:
            cls._config = cls._get_default_config()
            cls._loaded = True
    
    @classmethod
    def _get_default_config(cls) -> Dict:
        return {
            "model": {
                "type": "ADP",
                "base_path": "baselines",
            },
            "server": {"host": "0.0.0.0", "port": 8000, "log_level": "info"}
        }
    
    @classmethod
    def get(cls, key: str, default=None):
        if not cls._loaded: cls.load()
        keys = key.split('.')
        value = cls._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    @classmethod
    def get_model_paths(cls) -> Dict[str, str]:
        base_path = cls.get('model.base_path', 'baselines')
        model_type = cls.get('model.type', 'ADP')
        model_dir = f"douzero_{model_type}"
        return {
            'landlord': cls.get('model.paths.landlord', '') or os.path.join(base_path, model_dir, 'landlord.ckpt'),
            'landlord_up': cls.get('model.paths.landlord_up', '') or os.path.join(base_path, model_dir, 'landlord_up.ckpt'),
            'landlord_down': cls.get('model.paths.landlord_down', '') or os.path.join(base_path, model_dir, 'landlord_down.ckpt'),
        }

class ModelManager:
    def __init__(self):
        self.models = {}
        self.loaded = False

    def load_models(self):
        paths = Config.get_model_paths()
        try:
            for position, path in paths.items():
                self.models[position] = DeepAgent(position, path)
            self.loaded = True
            logger.info("✅ 模型加载成功")
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            self.loaded = False

    def get_model(self, position: str) -> DeepAgent:
        if not self.loaded:
            raise HTTPException(status_code=503, detail="模型未加载")
        if position not in self.models:
            raise HTTPException(status_code=400, detail=f"无效位置: {position}")
        return self.models[position]

model_manager = ModelManager()
douzero_service = DouZeroService(model_manager)


# ============ Hand Evaluation Utilities ============
def calculate_hand_strength(cards: List[int]) -> float:
    """启发式计算手牌强度 (0-1)，在模型加载失败时作为回退"""
    if not cards:
        return 0.0

    from collections import Counter
    counter = Counter(cards)
    score = 0.0

    for card, count in counter.items():
        if card == 30: score += 0.08 * count
        elif card == 20: score += 0.06 * count
        elif card == 17: score += 0.04 * count
        elif card == 14: score += 0.03 * count
        elif card == 13: score += 0.02 * count
        elif card == 12: score += 0.015 * count
        elif card == 11: score += 0.01 * count

    for card, count in counter.items():
        if count == 4: score += 0.1
        if (card == 20 or card == 30) and count >= 1: score += 0.05

    return min(score, 1.0)

def predict_hand_value(hand_cards: List[int], three_landlord_cards: List[int] = None) -> float:
    """利用 DouZero 打牌模型 (LSTM) 估算手牌价值。返回 Q-Value (大致在 -1 到 1 之间)"""
    from douzero.env.game import InfoSet
    from douzero.env.env import get_obs
    from douzero.env.move_generator import MovesGener
    
    total_cards = len(hand_cards) + (len(three_landlord_cards) if three_landlord_cards else 0)
    position = 'landlord' if total_cards >= 20 else 'landlord_up'
    
    try:
        agent = model_manager.get_model(position)
    except Exception:
        # 回退：将 0-1 的启发式强度映射回大致的 -1 到 1 区间
        return (calculate_hand_strength(hand_cards) - 0.5) * 2
    
    full_hand = copy.deepcopy(hand_cards)
    if three_landlord_cards and position == 'landlord':
        full_hand.extend(three_landlord_cards)
        
    infoset = InfoSet(position)
    infoset.player_hand_cards = full_hand
    
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
    
    # 计算 other_hand_cards：全集减去当前手牌
    from api.utils import ALL_ENV_CARDS
    other_hand_cards = []
    for card in set(ALL_ENV_CARDS):
        count = ALL_ENV_CARDS.count(card) - full_hand.count(card)
        other_hand_cards.extend([card] * count)
    infoset.other_hand_cards = sorted(other_hand_cards)
    
    if position == 'landlord':
        infoset.num_cards_left_dict = {'landlord': len(full_hand), 'landlord_up': 17, 'landlord_down': 17}
    else:
        infoset.num_cards_left_dict = {'landlord': 20, 'landlord_up': len(full_hand), 'landlord_down': 17}
        
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
        
        # 返回所有动作中最大的 Q-value
        return float(np.max(y_pred))
    except Exception:
        return (calculate_hand_strength(full_hand) - 0.5) * 2


# ============ FastAPI Application ============
app = FastAPI(
    title="DouZero API V2",
    description="Refactored DouZero API compatible with douzero_agent interface",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 DouZero API V2 启动中...")
    Config.load()
    model_manager.load_models()

@app.get("/health", response_model=HealthResponse)
@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy" if model_manager.loaded else "unhealthy",
        agent_initialized=model_manager.loaded
    )

@app.post("/api/play", response_model=ActionResponse)
async def get_best_action(request: PlayRequest):
    try:
        best_action, best_win_rate, _ = await run_in_threadpool(douzero_service.evaluate_action, request)
        
        action_type = ActionTypeDetector.detect(best_action).value
        cards_str = CardConverter.env_to_real(best_action)
        
        response = ActionResponse(
            cards=cards_str,
            win_rate=best_win_rate,
            action_type=action_type,
            confidence=best_win_rate,
            is_pass=(cards_str == ""),
            is_bomb=(action_type in ("bomb", "rocket"))
        )
        _log_play(request, response)
        return response
    except Exception as e:
        logger.exception("Error processing play request")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/actions", response_model=ActionsResponse)
async def get_all_actions(request: PlayRequest):
    try:
        best_action, best_win_rate, action_list = await run_in_threadpool(douzero_service.evaluate_action, request)
        
        actions = []
        for action, win_rate in action_list:
            act_type = ActionTypeDetector.detect(action).value
            c_str = CardConverter.env_to_real(action)
            actions.append(ActionResponse(
                cards=c_str,
                win_rate=win_rate,
                action_type=act_type,
                confidence=win_rate,
                is_pass=(c_str == ""),
                is_bomb=(act_type in ("bomb", "rocket"))
            ))
            
        best_type = ActionTypeDetector.detect(best_action).value
        best_str = CardConverter.env_to_real(best_action)
        best_resp = ActionResponse(
            cards=best_str,
            win_rate=best_win_rate,
            action_type=best_type,
            confidence=best_win_rate,
            is_pass=(best_str == ""),
            is_bomb=(best_type in ("bomb", "rocket"))
        )
        
        resp = ActionsResponse(
            best_action=best_resp,
            actions=actions,
            total_count=len(actions)
        )
        _log_actions(request.position, request.my_cards, resp)
        return resp
    except Exception as e:
        logger.exception("Error processing actions request")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bid", response_model=BidResponse)
async def evaluate_bid(request: BidRequest):
    try:
        env_cards = CardConverter.real_to_env(request.cards)
        strength = await run_in_threadpool(predict_hand_value, env_cards)
        
        # 根据模型胜率预测决定叫分
        if strength >= 0.4:
            bid = 3
        elif strength >= 0.1:
            bid = 2
        elif strength >= -0.2:
            bid = 1
        else:
            bid = 0
            
        should_bid = bid > 0
        
        # 将 Q-Value 粗略映射为 0-1 的胜率用于客户端展示
        win_rate = max(0.0, min(1.0, (strength + 1.0) / 2.0))
        
        resp = BidResponse(
            should_bid=should_bid,
            win_rate=win_rate,
            farmer_win_rate=1.0 - win_rate,
            confidence=strength
        )
        _log_bid(request.cards, resp)
        return resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/double", response_model=DoubleResponse)
async def evaluate_double(request: DoubleRequest):
    try:
        env_cards = CardConverter.real_to_env(request.cards)
        strength = await run_in_threadpool(predict_hand_value, env_cards)

        opponent_strength = 0.0
        if request.landlord_cards:
            ll_cards_env = CardConverter.real_to_env(request.landlord_cards)
            opponent_strength = await run_in_threadpool(predict_hand_value, ll_cards_env)

        if request.is_landlord:
            should_double = False # 地主在 DouZero 原始逻辑中不主动加倍
            should_super_double = False
        else:
            if strength > opponent_strength + 0.3:
                should_super_double = True
                should_double = True
            elif strength >= 0.2:
                should_super_double = False
                should_double = True
            else:
                should_super_double = False
                should_double = False
                
        # 将 Q-Value 粗略映射为 0-1 的胜率用于客户端展示
        win_rate = max(0.0, min(1.0, (strength + 1.0) / 2.0))
        
        resp = DoubleResponse(
            should_double=should_double,
            should_super_double=should_super_double,
            win_rate=win_rate,
            confidence=strength
        )
        _log_double(request.cards, request.is_landlord, resp)
        return resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    Config.load()
    logger.info("=" * 50)
    logger.info("🎮 DouZero API V2 服务 (douzero_agent 兼容接口)")
    logger.info("=" * 50)
    uvicorn.run(
        "api_server:app",
        host=Config.get('server.host', '0.0.0.0'),
        port=Config.get('server.port', 8000),
        log_level=Config.get('server.log_level', 'info')
    )
