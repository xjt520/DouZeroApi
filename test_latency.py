import requests
import time

BASE_URL = "http://127.0.0.1:8000"

# 牌值映射：数值 -> 字符
ENV_TO_STR = {3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
              10: 'T', 11: 'J', 12: 'Q', 13: 'K', 14: 'A', 17: '2', 20: 'X', 30: 'D'}

def cards_to_str(cards):
    """将数值列表转换为字符串格式"""
    return ''.join(ENV_TO_STR.get(c, str(c)) for c in cards)

def test_endpoint(name, method, url, payload=None):
    start_time = time.time()
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        end_time = time.time()
        elapsed = (end_time - start_time) * 1000
        print(f"✅ {name: <15} 耗时: {elapsed:.2f} ms")
        return response.json()
    except Exception as e:
        end_time = time.time()
        elapsed = (end_time - start_time) * 1000
        print(f"❌ {name: <15} 失败: {e} (耗时: {elapsed:.2f} ms)")
        return None

def main():
    print("等待服务器启动...")
    for _ in range(30):
        try:
            requests.get(f"{BASE_URL}/api/health", timeout=1)
            break
        except:
            time.sleep(1)
    else:
        print("服务器未能启动。")
        return

    print("开始测试接口延迟...\n")

    # 1. Health
    test_endpoint("Health", "GET", f"{BASE_URL}/api/health")

    # 2. Bid
    bid_payload = {
        "cards": "3456789TJQKA22X"
    }
    test_endpoint("Bid", "POST", f"{BASE_URL}/api/bid", bid_payload)

    # 3. Double (农民)
    double_payload = {
        "cards": "3456789TJQKA22X",
        "is_landlord": False,
        "landlord_cards": "345678"
    }
    test_endpoint("Double", "POST", f"{BASE_URL}/api/double", double_payload)

    # 4. Play
    play_payload = {
        "position": "landlord",
        "my_cards": "3456789TJQKA22XD",
        "played_cards": {
            "landlord": "",
            "landlord_up": "",
            "landlord_down": ""
        },
        "last_moves": [],
        "landlord_cards": "2XD",
        "cards_left": {
            "landlord": 20,
            "landlord_up": 17,
            "landlord_down": 17
        },
        "bomb_count": 0
    }
    test_endpoint("Play", "POST", f"{BASE_URL}/api/play", play_payload)

    # 5. Actions (全量建议)
    test_endpoint("Actions", "POST", f"{BASE_URL}/api/actions", play_payload)

if __name__ == "__main__":
    main()
