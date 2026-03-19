import requests
import json

BASE_URL = "http://localhost:8000"

def call_play(payload):
    return requests.post(f"{BASE_URL}/api/play", json=payload).json()

def call_bid(cards):
    return requests.post(f"{BASE_URL}/api/bid", json={"cards": cards}).json()

def print_case(title, result, expected_desc):
    status = "✅" if not result.get("isError") else "❌"
    print(f"{status} {title}")
    print(f"   输入手牌: {result.get('_input_hand', 'N/A')}")
    print(f"   上家出牌: {result.get('_last_moves', 'N/A')}")
    print(f"   AI 建议: {result.get('cards') or '[不出]'} ({result.get('action_type')})")
    print(f"   预测胜率: {result.get('win_rate', 0):.2%}")
    print(f"   预期行为: {expected_desc}")
    print("-" * 50)

def test_accuracy():
    print("开始 DouZeroApi 准确性深度测试...\n")
    
    # --- 出牌准确性测试 ---
    
    # Case 1: 绝对压制 (我有大牌，且必须压死)
    c1 = {
        "position": "landlord",
        "my_cards": "22AA",
        "played_cards": {"landlord": "", "landlord_up": "", "landlord_down": ""},
        "last_moves": ["KK"],
        "landlord_cards": "",
        "cards_left": {"landlord": 4, "landlord_up": 17, "landlord_down": 17}
    }
    res1 = call_play(c1)
    res1.update({"_input_hand": "22AA", "_last_moves": "KK"})
    print_case("Case 1: 绝对压制", res1, "应该出 AA 或 22")

    # Case 2: 王炸判定 (面对炸弹，我有王炸是否打出)
    c2 = {
        "position": "landlord",
        "my_cards": "XD345",
        "played_cards": {"landlord": "", "landlord_up": "", "landlord_down": ""},
        "last_moves": ["8888"],
        "landlord_cards": "",
        "cards_left": {"landlord": 5, "landlord_up": 2, "landlord_down": 10}
    }
    res2 = call_play(c2)
    res2.update({"_input_hand": "XD345", "_last_moves": "8888"})
    print_case("Case 2: 王炸判定", res2, "建议出 XD (王炸) 或判定胜率决定是否 Pass")

    # Case 3: 顺子保持 (不应轻易拆散长顺子)
    c3 = {
        "position": "landlord_down",
        "my_cards": "34567",
        "played_cards": {"landlord": "", "landlord_up": "", "landlord_down": ""},
        "last_moves": ["J"],
        "landlord_cards": "",
        "cards_left": {"landlord": 10, "landlord_up": 10, "landlord_down": 5}
    }
    res3 = call_play(c3)
    res3.update({"_input_hand": "34567", "_last_moves": "J"})
    print_case("Case 3: 策略合理性", res3, "手牌全是顺子，面对大牌 J，理应 Pass 不拆顺子")

    # Case 4: 最后一手 (手牌只剩一张且能大过对方)
    c4 = {
        "position": "landlord",
        "my_cards": "2",
        "played_cards": {"landlord": "", "landlord_up": "", "landlord_down": ""},
        "last_moves": ["A"],
        "landlord_cards": "",
        "cards_left": {"landlord": 1, "landlord_up": 10, "landlord_down": 10}
    }
    res4 = call_play(c4)
    res4.update({"_input_hand": "2", "_last_moves": "A"})
    print_case("Case 4: 终局判定", res4, "必须出 2，直接走人")

    # Case 5: 无法压制 (手牌全小，必须 Pass)
    c5 = {
        "position": "landlord_up",
        "my_cards": "3456",
        "played_cards": {"landlord": "", "landlord_up": "", "landlord_down": ""},
        "last_moves": ["T"],
        "landlord_cards": "",
        "cards_left": {"landlord": 10, "landlord_up": 4, "landlord_down": 10}
    }
    res5 = call_play(c5)
    res5.update({"_input_hand": "3456", "_last_moves": "T"})
    print_case("Case 5: 合法性检查", res5, "必须建议 Pass")

    # --- 叫分准确性测试 ---

    # Case 6: 极品好牌 (四炸+2+王)
    res6 = call_bid("2222AAAAKKKKQQQQX")
    print(f"✅ Case 6: 极品好牌叫分\n   手牌: 2222AAAAKKKKQQQQX\n   建议: {'叫地主' if res6['should_bid'] else '不叫'}\n   胜率: {res6['win_rate']:.2%}\n   预期: 叫地主")
    print("-" * 50)

    # Case 7: 极差牌 (全是小单张)
    res7 = call_bid("345789TJ345789TJQ")
    print(f"✅ Case 7: 极差牌叫分\n   手牌: 345789TJ345789TJQ\n   建议: {'叫地主' if res6['should_bid'] else '不叫'}\n   胜率: {res7['win_rate']:.2%}\n   预期: 不叫")
    print("-" * 50)

    # Case 8: 配合判定 (农民队友出 A，我也大，是否接牌)
    c8 = {
        "position": "landlord_up", # 农民上家
        "my_cards": "22",
        "played_cards": {"landlord": "33", "landlord_up": "", "landlord_down": "A"}, # 下家(队友)刚出了 A
        "last_moves": ["A"],
        "landlord_cards": "",
        "cards_left": {"landlord": 15, "landlord_up": 2, "landlord_down": 5}
    }
    res8 = call_play(c8)
    res8.update({"_input_hand": "22", "_last_moves": "A"})
    print_case("Case 8: 农民配合", res8, "队友出的 A，如果 AI 聪明应该 Pass 让队友继续走")

if __name__ == "__main__":
    test_accuracy()
