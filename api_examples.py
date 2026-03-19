"""
DouZero API 调用示例
演示如何使用 REST API 获取出牌、叫分、加倍建议
"""

import requests
import json
from typing import List, Dict

# API 基础 URL
BASE_URL = "http://localhost:8000"

# ============ 辅助函数 ============

def print_response(title: str, response: dict):
    """美化打印响应"""
    print(f"\n{'='*60}")
    print(f"📌 {title}")
    print(f"{'='*60}")
    print(json.dumps(response, ensure_ascii=False, indent=2))

def cards_to_list(cards_str: str) -> List[int]:
    """将牌面字符串转换为数值列表"""
    card_map = {
        '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
        'J': 11, 'Q': 12, 'K': 13, 'A': 14, '2': 17,
        '小王': 20, '大王': 30
    }
    result = []
    for card in cards_str.split():
        result.append(card_map.get(card, int(card)))
    return result

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

    request_data = {
        "position": "landlord",
        "player_hand_cards": [5, 6, 8, 11, 14, 17],
        "card_play_action_seq": [[], [3], [], [5]],
        "three_landlord_cards": [17, 20, 30],
        "bomb_num": 0
    }

    print(f"📤 请求数据: {json.dumps(request_data, ensure_ascii=False)}")

    response = requests.post(
        f"{BASE_URL}/api/act",
        json=request_data
    )

    print_response("出牌建议响应", response.json())

    result = response.json()
    print(f"\n💡 建议出牌: {result['action_str']}")
    print(f"   置信度: {result['confidence']:.2%}")
    print(f"   合法出牌数: {len(result['legal_actions'])}")

def example_get_action_farmer():
    """示例 3: 农民获取出牌建议"""
    print("\n🎴 示例 3: 农民获取出牌建议")

    request_data = {
        "position": "landlord_up",
        "player_hand_cards": [3, 7, 9, 10, 12, 13, 14],
        "card_play_action_seq": [[], [3], [], [5], [], [8]],
        "three_landlord_cards": [17, 20, 30],
        "bomb_num": 0
    }

    print(f"📤 请求数据: {json.dumps(request_data, ensure_ascii=False)}")

    response = requests.post(
        f"{BASE_URL}/api/act",
        json=request_data
    )

    print_response("出牌建议响应", response.json())

def example_get_bid():
    """示例 4: 获取叫分建议"""
    print("\n🎯 示例 4: 获取叫分建议")

    # 示例 1: 强牌叫分
    request_data = {
        "position": "landlord_up",
        "hand_cards": [3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 14, 17, 17],
        "three_landlord_cards": [17, 20, 30]
    }

    print(f"📤 请求数据 (强牌): {json.dumps(request_data, ensure_ascii=False)}")

    response = requests.post(
        f"{BASE_URL}/api/bid",
        json=request_data
    )

    print_response("叫分建议响应 (强牌)", response.json())

    # 示例 2: 弱牌叫分
    request_data_weak = {
        "position": "landlord_down",
        "hand_cards": [3, 3, 5, 6, 8, 9, 10, 12, 13, 14]
    }

    print(f"\n📤 请求数据 (弱牌): {json.dumps(request_data_weak, ensure_ascii=False)}")

    response_weak = requests.post(
        f"{BASE_URL}/api/bid",
        json=request_data_weak
    )

    print_response("叫分建议响应 (弱牌)", response_weak.json())

def example_get_double():
    """示例 5: 获取加倍建议"""
    print("\n⚡ 示例 5: 获取加倍建议")

    request_data = {
        "position": "landlord_up",
        "hand_cards": [3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 14, 17, 17],
        "current_landlord_score": 2,
        "landlord_cards": []
    }

    print(f"📤 请求数据: {json.dumps(request_data, ensure_ascii=False)}")

    response = requests.post(
        f"{BASE_URL}/api/double",
        json=request_data
    )

    print_response("加倍建议响应", response.json())

def example_complete_game_flow():
    """示例 6: 完整游戏流程模拟"""
    print("\n🎮 示例 6: 完整游戏流程模拟")

    # 游戏初始化
    game_state = {
        "landlord_cards": [5, 6, 8, 11, 14, 17],
        "landlord_up_cards": [3, 7, 9, 10, 12, 13, 14],
        "landlord_down_cards": [4, 5, 7, 8, 9, 11, 13],
        "action_sequence": [],
        "bomb_num": 0
    }

    print("\n📋 初始手牌:")
    print(f"   地主: {cards_to_list(game_state['landlord_cards'])}")
    print(f"   上家: {cards_to_list(game_state['landlord_up_cards'])}")
    print(f"   下家: {cards_to_list(game_state['landlord_down_cards'])}")

    # 模拟几轮出牌
    rounds = [
        {"position": "landlord", "action": [5]},
        {"position": "landlord_up", "action": [7]},
        {"position": "landlord_down", "action": []},  # 过
    ]

    for round_num, round_data in enumerate(rounds, 1):
        print(f"\n📍 第 {round_num} 轮 - {round_data['position']} 出牌:")

        # 添加到动作序列
        game_state["action_sequence"].append(round_data["action"])

        # 更新手牌
        position = round_data["position"]
        if position == "landlord":
            hand_key = "landlord_cards"
        elif position == "landlord_up":
            hand_key = "landlord_up_cards"
        else:
            hand_key = "landlord_down_cards"

        # 移除已出的牌
        for card in round_data["action"]:
            if card in game_state[hand_key]:
                game_state[hand_key].remove(card)

        # 获取建议
        next_position = "landlord" if position == "landlord_down" else \
                       "landlord_up" if position == "landlord" else "landlord_down"

        next_hand_key = "landlord_cards" if next_position == "landlord" else \
                       "landlord_up_cards" if next_position == "landlord_up" else "landlord_down_cards"

        request_data = {
            "position": next_position,
            "player_hand_cards": game_state[next_hand_key],
            "card_play_action_seq": game_state["action_sequence"],
            "three_landlord_cards": [17, 20, 30],
            "bomb_num": game_state["bomb_num"]
        }

        response = requests.post(f"{BASE_URL}/api/act", json=request_data)
        result = response.json()

        print(f"   💡 建议出牌: {result['action_str']}")
        print(f"   📊 置信度: {result['confidence']:.2%}")
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
        "player_hand_cards": [5, 6, 8, 11, 14, 17],
        "card_play_action_seq": [[], [3], [], [5]],
        "three_landlord_cards": [17, 20, 30],
        "bomb_num": 0
    }

    try:
        response = requests.post(f"{BASE_URL}/api/act", json=request_data)
        result = response.json()
        print(f"\n✅ 建议出牌: {result['action_str']}")
        print(f"   置信度: {result['confidence']:.2%}")
        print(f"   合法出牌数: {len(result['legal_actions'])}")
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
