"""
DouZero API 调用示例
演示如何使用 REST API 获取出牌、叫分、加倍建议
"""

import requests
import json
from typing import List

# API 基础 URL
BASE_URL = "http://localhost:8000"

# ============ 辅助函数 ============

def print_response(title: str, response: dict):
    """美化打印响应"""
    print(f"\n{'='*60}")
    print(f"📌 {title}")
    print(f"{'='*60}")
    print(json.dumps(response, ensure_ascii=False, indent=2))

def cards_to_str(cards: List[str]) -> str:
    """将牌面列表转换为字符串"""
    return "".join(cards)

# ============ API 调用示例 ============

def example_health_check():
    """示例 1: 健康检查"""
    print("\n🔍 示例 1: 健康检查")
    response = requests.get(f"{BASE_URL}/api/health")
    print_response("健康检查响应", response.json())
    return response.json()['status'] == 'healthy'

def example_get_action_landlord():
    """示例 2: 地主获取出牌建议"""
    print("\n🎴 示例 2: 地主获取出牌建议")

    # 注意：played_cards 必须是全量累计（从开局到当前的所有出牌）
    # cards_left 强烈建议提供，确保模型推理准确
    request_data = {
        "position": "landlord",
        "my_cards": "568AJ2",
        "played_cards": {
            "landlord": "34",          # 地主已出的所有牌（累计）
            "landlord_up": "7",        # 上家已出的所有牌（累计）
            "landlord_down": ""        # 下家还没出过牌
        },
        "last_moves": ["7", "5"],      # 最近几轮出牌
        "landlord_cards": "2XD",
        "cards_left": {
            "landlord": 6,
            "landlord_up": 16,
            "landlord_down": 17
        },
        "bomb_count": 0
    }

    print(f"📤 请求数据: {json.dumps(request_data, ensure_ascii=False)}")

    response = requests.post(
        f"{BASE_URL}/api/play",
        json=request_data
    )

    print_response("出牌建议响应", response.json())

    result = response.json()
    cards_str = result['cards'] if result['cards'] else "[不出]"
    print(f"\n💡 建议出牌: {cards_str}")
    print(f"   胜率: {result['win_rate']:.2%}")
    print(f"   牌型: {result['action_type']}")

def example_get_action_farmer():
    """示例 3: 农民获取出牌建议"""
    print("\n🎴 示例 3: 农民获取出牌建议")

    # played_cards 是全量累计，cards_left 用于验证剩余牌数
    request_data = {
        "position": "landlord_up",
        "my_cards": "379TKA",
        "played_cards": {
            "landlord": "345",         # 地主已出: 3,4,5
            "landlord_up": "6",        # 我已出: 6
            "landlord_down": ""        # 下家还没出
        },
        "last_moves": ["8", "5"],      # 最近出牌记录
        "landlord_cards": "2XD",
        "cards_left": {
            "landlord": 17,
            "landlord_up": 6,
            "landlord_down": 17
        },
        "bomb_count": 0
    }

    print(f"📤 请求数据: {json.dumps(request_data, ensure_ascii=False)}")

    response = requests.post(
        f"{BASE_URL}/api/play",
        json=request_data
    )

    print_response("出牌建议响应", response.json())

def example_get_all_actions():
    """示例 4: 获取所有出牌建议"""
    print("\n📋 示例 4: 获取所有出牌建议")

    request_data = {
        "position": "landlord",
        "my_cards": "568AJ2",
        "last_moves": ["3", "5"],
        "landlord_cards": "2XD"
    }

    print(f"📤 请求数据: {json.dumps(request_data, ensure_ascii=False)}")

    response = requests.post(
        f"{BASE_URL}/api/actions",
        json=request_data
    )

    result = response.json()
    print(f"\n最佳出牌: {result['best_action']['cards']} (胜率: {result['best_action']['win_rate']:.2%})")
    print(f"\n所有可选出牌 (共 {result['total_count']} 种):")
    for i, action in enumerate(result['actions'][:10], 1):
        cards_str = action['cards'] if action['cards'] else "[不出]"
        mark = "★" if action['cards'] == result['best_action']['cards'] else " "
        print(f"  {mark}{i}. {cards_str:<10} | {action['action_type']:<10} | 胜率: {action['win_rate']:.1%}")

def example_get_bid():
    """示例 5: 获取叫分建议"""
    print("\n🎯 示例 5: 获取叫分建议")

    # 示例 1: 强牌叫分
    request_data = {
        "cards": "345789TJQQAA22"
    }

    print(f"📤 请求数据 (强牌): {json.dumps(request_data, ensure_ascii=False)}")

    response = requests.post(
        f"{BASE_URL}/api/bid",
        json=request_data
    )

    print_response("叫分建议响应 (强牌)", response.json())

    # 示例 2: 弱牌叫分
    request_data_weak = {
        "cards": "335689TQK"
    }

    print(f"\n📤 请求数据 (弱牌): {json.dumps(request_data_weak, ensure_ascii=False)}")

    response_weak = requests.post(
        f"{BASE_URL}/api/bid",
        json=request_data_weak
    )

    print_response("叫分建议响应 (弱牌)", response_weak.json())

def example_get_double():
    """示例 6: 获取加倍建议"""
    print("\n⚡ 示例 6: 获取加倍建议")

    request_data = {
        "cards": "345789TJQQAA22",
        "is_landlord": False,
        "landlord_cards": "3344556"
    }

    print(f"📤 请求数据: {json.dumps(request_data, ensure_ascii=False)}")

    response = requests.post(
        f"{BASE_URL}/api/double",
        json=request_data
    )

    print_response("加倍建议响应", response.json())

def example_complete_game_flow():
    """示例 7: 完整游戏流程模拟"""
    print("\n🎮 示例 7: 完整游戏流程模拟")

    # 游戏初始化
    # 注意：played_cards 必须累计所有已出的牌
    game_state = {
        "landlord_cards": "568AJ2",
        "landlord_up_cards": "379TKA",
        "landlord_down_cards": "45789JK",
        "played_cards": {
            "landlord": "",
            "landlord_up": "",
            "landlord_down": ""
        },
        "last_moves": [],
        "bomb_count": 0
    }

    print("\n📋 初始手牌:")
    print(f"   地主: {game_state['landlord_cards']}")
    print(f"   上家: {game_state['landlord_up_cards']}")
    print(f"   下家: {game_state['landlord_down_cards']}")

    # 模拟几轮出牌
    rounds = [
        {"position": "landlord", "cards": "5"},
        {"position": "landlord_up", "cards": "7"},
        {"position": "landlord_down", "cards": ""},  # 过
    ]

    position_hand_map = {
        "landlord": "landlord_cards",
        "landlord_up": "landlord_up_cards",
        "landlord_down": "landlord_down_cards"
    }

    for round_num, round_data in enumerate(rounds, 1):
        print(f"\n📍 第 {round_num} 轮 - {round_data['position']} 出牌:")

        position = round_data["position"]
        played = round_data["cards"]
        
        # 累计更新已出牌（关键：必须是累计而非覆盖）
        if played:
            game_state["played_cards"][position] += played
        game_state["last_moves"].append(played)
        if len(game_state["last_moves"]) > 3:
            game_state["last_moves"].pop(0)

        # 更新手牌 (简单模拟，实际应该移除对应的牌)
        hand_key = position_hand_map[position]
        if played:
            current_hand = game_state[hand_key]
            for card in played:
                current_hand = current_hand.replace(card, "", 1)
            game_state[hand_key] = current_hand

        # 获取下一个玩家的建议
        positions = ["landlord", "landlord_down", "landlord_up"]
        current_idx = positions.index(position)
        next_position = positions[(current_idx + 1) % 3]
        next_hand_key = position_hand_map[next_position]

        # 计算 cards_left（强烈建议提供）
        cards_left = {
            "landlord": len(game_state["landlord_cards"]),
            "landlord_up": len(game_state["landlord_up_cards"]),
            "landlord_down": len(game_state["landlord_down_cards"])
        }

        request_data = {
            "position": next_position,
            "my_cards": game_state[next_hand_key],
            "played_cards": game_state["played_cards"],  # 全量累计
            "last_moves": game_state["last_moves"],
            "landlord_cards": "2XD",
            "cards_left": cards_left,
            "bomb_count": game_state["bomb_count"]
        }

        response = requests.post(f"{BASE_URL}/api/play", json=request_data)
        result = response.json()

        cards_str = result['cards'] if result['cards'] else "[不出]"
        print(f"   💡 建议出牌: {cards_str}")
        print(f"   📊 胜率: {result['win_rate']:.2%}")
        print(f"   🃏 剩余手牌: {game_state[next_hand_key]}")

# ============ 主函数 ============

def main():
    """运行所有示例"""
    print("="*60)
    print("🎮 DouZero API 调用示例")
    print("="*60)

    try:
        # 健康检查
        if not example_health_check():
            print("\n❌ 服务未启动，请先运行: python3 api_server.py")
            return

        # 运行示例
        example_get_action_landlord()
        example_get_action_farmer()
        example_get_all_actions()
        example_get_bid()
        example_get_double()
        example_complete_game_flow()

        print("\n" + "="*60)
        print("✅ 所有示例运行完成！")
        print("="*60)

    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到 API 服务")
        print("💡 请确保服务正在运行: python3 api_server.py")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

# ============ 快速测试函数 ============

def quick_test():
    """快速测试：只测试出牌建议"""
    print("\n⚡ 快速测试")

    request_data = {
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
    }

    try:
        response = requests.post(f"{BASE_URL}/api/play", json=request_data)
        result = response.json()
        cards_str = result['cards'] if result['cards'] else "[不出]"
        print(f"\n✅ 建议出牌: {cards_str}")
        print(f"   胜率: {result['win_rate']:.2%}")
        print(f"   牌型: {result['action_type']}")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        quick_test()
    else:
        main()
