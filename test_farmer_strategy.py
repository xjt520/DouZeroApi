import requests
import json

BASE_URL = "http://localhost:8000"

def test_lead_strategy(title, cards_left_teammate, my_cards):
    payload = {
        "position": "landlord_up", # 农民上家
        "my_cards": my_cards,
        "played_cards": {"landlord": "55", "landlord_up": "88", "landlord_down": ""},
        "last_moves": [], # 领出牌阶段
        "landlord_cards": "XD2",
        "cards_left": {
            "landlord": 10,
            "landlord_up": len(my_cards),
            "landlord_down": cards_left_teammate # 观察队友剩余牌数对我的影响
        }
    }
    res = requests.post(f"{BASE_URL}/api/play", json=payload).json()
    print(f"测试场景: {title}")
    print(f"   我的手牌: {my_cards}")
    print(f"   队友(下家)剩余: {cards_left_teammate} 张")
    print(f"   AI 建议领出: {res.get('cards') or '[不出]'} ({res.get('action_type')})")
    print(f"   预测胜率: {res.get('win_rate', 0):.2%}")
    print("-" * 50)

if __name__ == "__main__":
    print("正在测试农民领出牌策略...\n")
    
    # 场景 A: 队友牌很多，我自己牌一般，看是出大牌还是小牌
    test_lead_strategy("场景 A (队友牌多，保守起见)", 17, "33AA22")
    
    # 场景 B: 队友只剩 1 张牌，看我是否会出小单张“喂”队友
    test_lead_strategy("场景 B (队友剩1张，疑似喂牌)", 1, "33AA22")
    
    # 场景 C: 我自己快跑完了（只剩 33 和 王炸），看是否直接冲大牌
    test_lead_strategy("场景 C (自己快跑完，冲刺)", 10, "33XD")
