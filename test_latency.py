import requests
import time

BASE_URL = "http://127.0.0.1:8000"

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
            requests.get(f"{BASE_URL}/", timeout=1)
            break
        except:
            time.sleep(1)
    else:
        print("服务器未能启动。")
        return

    print("开始测试接口延迟...\n")

    # 1. Health
    test_endpoint("Health", "GET", f"{BASE_URL}/api/health")

    # 2. Deal
    deal_res = test_endpoint("Deal", "GET", f"{BASE_URL}/api/deal")
    if not deal_res:
        return

    landlord_cards = deal_res["landlord"]
    landlord_up_cards = deal_res["landlord_up"]
    three_landlord_cards = deal_res["three_landlord_cards"]

    # 3. Bid
    bid_payload = {
        "position": "landlord_up",
        "hand_cards": landlord_up_cards,
        "three_landlord_cards": three_landlord_cards
    }
    test_endpoint("Bid", "POST", f"{BASE_URL}/api/bid", bid_payload)

    # 4. Double
    double_payload = {
        "position": "landlord_up",
        "hand_cards": landlord_up_cards,
        "current_landlord_score": 2,
        "landlord_cards": landlord_cards
    }
    test_endpoint("Double", "POST", f"{BASE_URL}/api/double", double_payload)

    # 5. Act
    act_payload = {
        "position": "landlord",
        "player_hand_cards": landlord_cards,
        "card_play_action_seq": [],
        "three_landlord_cards": three_landlord_cards,
        "bomb_num": 0
    }
    test_endpoint("Act", "POST", f"{BASE_URL}/api/act", act_payload)

if __name__ == "__main__":
    main()
