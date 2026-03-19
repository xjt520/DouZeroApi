import requests
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from collections import Counter

BASE_URL = "http://localhost:8000"
CARDS = "3456789TJQKA2XD"
POSITIONS = ["landlord", "landlord_up", "landlord_down"]

def generate_random_hand(size=10):
    # 简单的随机手牌生成（非严格模拟发牌，但符合格式）
    deck = list("3333444455556666777788889999TTTTJJJJQQQQKKKKAAAA2222XD")
    hand = random.sample(deck, size)
    return "".join(sorted(hand, key=lambda x: CARDS.find(x)))

def generate_test_case():
    pos = random.choice(POSITIONS)
    my_hand_size = random.randint(1, 15)
    my_cards = generate_random_hand(my_hand_size)
    
    # 模拟最近一手的出牌 (50% 概率为空，50% 概率有 1-2 手)
    last_moves = []
    if random.random() > 0.5:
        move_type = random.choice(["single", "pair", "triple"])
        if move_type == "single": last_moves = [random.choice(CARDS[:-2])]
        elif move_type == "pair": c = random.choice(CARDS[:-2]); last_moves = [c+c]
    
    return {
        "position": pos,
        "my_cards": my_cards,
        "played_cards": {
            "landlord": generate_random_hand(random.randint(0, 5)),
            "landlord_up": generate_random_hand(random.randint(0, 5)),
            "landlord_down": generate_random_hand(random.randint(0, 5))
        },
        "last_moves": last_moves,
        "landlord_cards": generate_random_hand(3),
        "cards_left": {
            "landlord": random.randint(1, 20),
            "landlord_up": random.randint(1, 17),
            "landlord_down": random.randint(1, 17)
        },
        "bomb_count": random.randint(0, 2)
    }

def run_single_test(_):
    payload = generate_test_case()
    start_time = time.time()
    try:
        response = requests.post(f"{BASE_URL}/api/play", json=payload, timeout=5)
        latency = (time.time() - start_time) * 1000
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "latency": latency,
                "action_type": data.get("action_type", "unknown"),
                "is_pass": data.get("is_pass", False)
            }
        else:
            return {"success": False, "error": f"Status {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    total_tests = 1000
    print(f"🚀 开始执行 {total_tests} 个测试用例...")
    
    results = []
    start_wall_time = time.time()
    
    # 使用 10 个线程并发（模拟真实并发压力）
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(run_single_test, range(total_tests)))
    
    end_wall_time = time.time()
    
    # 数据汇总
    success_count = sum(1 for r in results if r["success"])
    latencies = [r["latency"] for r in results if r["success"]]
    action_types = [r["action_type"] for r in results if r["success"]]
    pass_count = sum(1 for r in results if r.get("is_pass", False))
    
    print("\n" + "="*50)
    print("📈 DouZeroApi 1000例测试报告")
    print("="*50)
    print(f"总请求数: {total_tests}")
    print(f"成功率: {(success_count/total_tests)*100:.2f}%")
    print(f"总耗时: {end_wall_time - start_wall_time:.2f} 秒")
    
    if latencies:
        print(f"平均延迟: {sum(latencies)/len(latencies):.2f} ms")
        print(f"最快响应: {min(latencies):.2f} ms")
        print(f"最慢响应: {max(latencies):.2f} ms")
    
    print("\n出牌类型分布:")
    type_counts = Counter(action_types)
    for act, count in type_counts.most_common():
        print(f"  - {act:<12}: {count} 次 ({(count/success_count)*100:.1f}%)")
    
    print(f"\n主动不出 (Pass) 次数: {pass_count}")
    print("="*50)

if __name__ == "__main__":
    main()
