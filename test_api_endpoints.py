import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_endpoint(name, method, path, data=None):
    url = f"{BASE_URL}{path}"
    start_time = time.time()
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        
        elapsed = (time.time() - start_time) * 1000
        status = "PASSED" if response.status_code == 200 else "FAILED"
        
        return {
            "name": name,
            "status": status,
            "code": response.status_code,
            "latency": f"{elapsed:.2f}ms",
            "response": response.json() if status == "PASSED" else response.text
        }
    except Exception as e:
        return {
            "name": name,
            "status": "ERROR",
            "error": str(e)
        }

def run_tests():
    results = []
    
    # 1. 健康检查
    results.append(test_endpoint("健康检查", "GET", "/api/health"))
    
    # 2. 叫分建议
    results.append(test_endpoint("叫分建议", "POST", "/api/bid", {
        "cards": "345789TJQQAA22"
    }))
    
    # 3. 加倍建议
    results.append(test_endpoint("加倍建议", "POST", "/api/double", {
        "cards": "345789TJQQAA22",
        "is_landlord": False,
        "landlord_cards": "3344556"
    }))
    
    # 4. 最佳出牌
    results.append(test_endpoint("最佳出牌", "POST", "/api/play", {
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
        }
    }))
    
    # 5. 全量动作建议
    results.append(test_endpoint("全量动作", "POST", "/api/actions", {
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
        }
    }))
    
    return results

if __name__ == "__main__":
    test_results = run_tests()
    print(json.dumps(test_results, indent=2, ensure_ascii=False))
