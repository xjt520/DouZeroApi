#!/usr/bin/env python3
"""
DouZero API 自动化测试脚本
测试所有 API 接口并生成测试报告
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple

BASE_URL = "http://localhost:8000"

class TestResult:
    def __init__(self, endpoint: str, method: str, name: str):
        self.endpoint = endpoint
        self.method = method
        self.name = name
        self.passed = False
        self.status_code = 0
        self.response_time_ms = 0
        self.response = None
        self.error = None
        self.test_cases: List[Dict] = []

    def to_dict(self) -> Dict:
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "name": self.name,
            "passed": self.passed,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "error": self.error,
            "test_cases": self.test_cases
        }


def test_health_endpoint() -> TestResult:
    """测试健康检查接口"""
    result = TestResult("/api/health", "GET", "健康检查接口")

    # 测试用例1: /api/health
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=10)
        result.status_code = r.status_code
        result.response_time_ms = round((time.time() - start) * 1000, 2)
        result.response = r.json()

        case1 = {
            "name": "GET /api/health",
            "passed": r.status_code == 200 and r.json().get("status") == "healthy",
            "status_code": r.status_code,
            "response": r.json()
        }
        result.test_cases.append(case1)
    except Exception as e:
        result.error = str(e)
        result.test_cases.append({"name": "GET /api/health", "passed": False, "error": str(e)})

    # 测试用例2: /health (别名)
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        case2 = {
            "name": "GET /health (别名)",
            "passed": r.status_code == 200 and r.json().get("status") == "healthy",
            "status_code": r.status_code,
            "response": r.json()
        }
        result.test_cases.append(case2)
    except Exception as e:
        result.test_cases.append({"name": "GET /health (别名)", "passed": False, "error": str(e)})

    result.passed = all(c.get("passed", False) for c in result.test_cases)
    return result


def test_play_endpoint() -> TestResult:
    """测试出牌建议接口"""
    result = TestResult("/api/play", "POST", "出牌建议接口")

    # 测试用例1: 地主出牌 - 基本场景
    test_cases_data = [
        {
            "name": "地主出牌 - 基本场景",
            "data": {
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
        },
        {
            "name": "农民(上家)出牌 - 需要跟牌",
            "data": {
                "position": "landlord_up",
                "my_cards": "3456789TJQKA2",
                "played_cards": {
                    "landlord": "X",
                    "landlord_up": "",
                    "landlord_down": ""
                },
                "last_moves": ["X", "", ""],
                "landlord_cards": "XD2",
                "cards_left": {
                    "landlord": 19,
                    "landlord_up": 17,
                    "landlord_down": 17
                },
                "bomb_count": 0
            }
        },
        {
            "name": "农民(下家)出牌 - 自由出牌",
            "data": {
                "position": "landlord_down",
                "my_cards": "33445566778899",
                "played_cards": {
                    "landlord": "",
                    "landlord_up": "",
                    "landlord_down": ""
                },
                "last_moves": [],
                "landlord_cards": "",
                "cards_left": {
                    "landlord": 20,
                    "landlord_up": 17,
                    "landlord_down": 14
                },
                "bomb_count": 0
            }
        },
        {
            "name": "地主出牌 - 有炸弹场景",
            "data": {
                "position": "landlord",
                "my_cards": "333344445566",
                "played_cards": {
                    "landlord": "",
                    "landlord_up": "7",
                    "landlord_down": "8"
                },
                "last_moves": ["8", "7"],
                "landlord_cards": "XD2",
                "cards_left": {
                    "landlord": 12,
                    "landlord_up": 16,
                    "landlord_down": 16
                },
                "bomb_count": 0
            }
        },
        {
            "name": "边界测试 - 只剩一张牌",
            "data": {
                "position": "landlord",
                "my_cards": "A",
                "played_cards": {
                    "landlord": "23456789TJQK",
                    "landlord_up": "23456789TJQKA2X",
                    "landlord_down": "23456789TJQKA2D"
                },
                "last_moves": ["2", "K"],
                "landlord_cards": "XD2",
                "cards_left": {
                    "landlord": 1,
                    "landlord_up": 0,
                    "landlord_down": 0
                },
                "bomb_count": 0
            }
        }
    ]

    for tc in test_cases_data:
        start = time.time()
        try:
            r = requests.post(f"{BASE_URL}/api/play", json=tc["data"], timeout=30)
            response_time = round((time.time() - start) * 1000, 2)

            case_result = {
                "name": tc["name"],
                "passed": False,
                "status_code": r.status_code,
                "response_time_ms": response_time
            }

            if r.status_code == 200:
                resp = r.json()
                case_result["response"] = resp
                # 验证响应结构
                required_fields = ["cards", "win_rate", "action_type", "confidence", "is_pass", "is_bomb"]
                has_all_fields = all(f in resp for f in required_fields)
                case_result["passed"] = has_all_fields
                case_result["validation"] = {
                    "has_required_fields": has_all_fields,
                    "cards": resp.get("cards"),
                    "action_type": resp.get("action_type"),
                    "win_rate": resp.get("win_rate")
                }
            else:
                case_result["error"] = r.text

            result.test_cases.append(case_result)
        except Exception as e:
            result.test_cases.append({
                "name": tc["name"],
                "passed": False,
                "error": str(e)
            })

    result.passed = all(c.get("passed", False) for c in result.test_cases)
    if result.test_cases:
        result.status_code = result.test_cases[0].get("status_code", 0)
        result.response_time_ms = max(c.get("response_time_ms", 0) for c in result.test_cases)

    return result


def test_actions_endpoint() -> TestResult:
    """测试全量出牌建议接口"""
    result = TestResult("/api/actions", "POST", "全量出牌建议接口")

    test_cases_data = [
        {
            "name": "地主获取所有出牌建议",
            "data": {
                "position": "landlord",
                "my_cards": "34567",
                "played_cards": {
                    "landlord": "",
                    "landlord_up": "",
                    "landlord_down": ""
                },
                "last_moves": [],
                "landlord_cards": "XD2",
                "cards_left": {
                    "landlord": 5,
                    "landlord_up": 17,
                    "landlord_down": 17
                },
                "bomb_count": 0
            }
        },
        {
            "name": "农民需要跟牌 - 获取所有可行方案",
            "data": {
                "position": "landlord_up",
                "my_cards": "33557799JJ",
                "played_cards": {
                    "landlord": "44",
                    "landlord_up": "",
                    "landlord_down": ""
                },
                "last_moves": ["44"],
                "landlord_cards": "",
                "cards_left": {
                    "landlord": 18,
                    "landlord_up": 10,
                    "landlord_down": 17
                },
                "bomb_count": 0
            }
        }
    ]

    for tc in test_cases_data:
        start = time.time()
        try:
            r = requests.post(f"{BASE_URL}/api/actions", json=tc["data"], timeout=30)
            response_time = round((time.time() - start) * 1000, 2)

            case_result = {
                "name": tc["name"],
                "passed": False,
                "status_code": r.status_code,
                "response_time_ms": response_time
            }

            if r.status_code == 200:
                resp = r.json()
                case_result["response"] = resp
                # 验证响应结构
                has_best = "best_action" in resp
                has_actions = "actions" in resp and isinstance(resp["actions"], list)
                has_count = "total_count" in resp

                case_result["passed"] = has_best and has_actions and has_count
                case_result["validation"] = {
                    "has_best_action": has_best,
                    "has_actions_list": has_actions,
                    "total_count": resp.get("total_count"),
                    "actions_count": len(resp.get("actions", []))
                }
            else:
                case_result["error"] = r.text

            result.test_cases.append(case_result)
        except Exception as e:
            result.test_cases.append({
                "name": tc["name"],
                "passed": False,
                "error": str(e)
            })

    result.passed = all(c.get("passed", False) for c in result.test_cases)
    if result.test_cases:
        result.status_code = result.test_cases[0].get("status_code", 0)
        result.response_time_ms = max(c.get("response_time_ms", 0) for c in result.test_cases)

    return result


def test_bid_endpoint() -> TestResult:
    """测试叫分建议接口"""
    result = TestResult("/api/bid", "POST", "叫分建议接口")

    test_cases_data = [
        {
            "name": "普通手牌 - 中等强度",
            "data": {
                "cards": "345789TJQQAA22"
            }
        },
        {
            "name": "强牌 - 有大小王",
            "data": {
                "cards": "3456XD2AAAA"
            }
        },
        {
            "name": "弱牌 - 无大牌",
            "data": {
                "cards": "3456788999TTJJ"
            }
        },
        {
            "name": "炸弹手牌",
            "data": {
                "cards": "3333456789TJQK"
            }
        }
    ]

    for tc in test_cases_data:
        start = time.time()
        try:
            r = requests.post(f"{BASE_URL}/api/bid", json=tc["data"], timeout=30)
            response_time = round((time.time() - start) * 1000, 2)

            case_result = {
                "name": tc["name"],
                "passed": False,
                "status_code": r.status_code,
                "response_time_ms": response_time
            }

            if r.status_code == 200:
                resp = r.json()
                case_result["response"] = resp
                # 验证响应结构
                required_fields = ["should_bid", "win_rate", "farmer_win_rate", "confidence"]
                has_all_fields = all(f in resp for f in required_fields)
                case_result["passed"] = has_all_fields
                case_result["validation"] = {
                    "has_required_fields": has_all_fields,
                    "should_bid": resp.get("should_bid"),
                    "win_rate": resp.get("win_rate")
                }
            else:
                case_result["error"] = r.text

            result.test_cases.append(case_result)
        except Exception as e:
            result.test_cases.append({
                "name": tc["name"],
                "passed": False,
                "error": str(e)
            })

    result.passed = all(c.get("passed", False) for c in result.test_cases)
    if result.test_cases:
        result.status_code = result.test_cases[0].get("status_code", 0)
        result.response_time_ms = max(c.get("response_time_ms", 0) for c in result.test_cases)

    return result


def test_double_endpoint() -> TestResult:
    """测试加倍建议接口"""
    result = TestResult("/api/double", "POST", "加倍建议接口")

    test_cases_data = [
        {
            "name": "农民 - 强牌加倍",
            "data": {
                "cards": "33445566778899TTJJ",
                "is_landlord": False,
                "landlord_cards": "3456789"
            }
        },
        {
            "name": "农民 - 弱牌不加倍",
            "data": {
                "cards": "3456789TTJJ",
                "is_landlord": False,
                "landlord_cards": "AAAA22XD"
            }
        },
        {
            "name": "地主 - 默认不加倍",
            "data": {
                "cards": "33445566778899TTJJQQ",
                "is_landlord": True
            }
        },
        {
            "name": "农民 - 超级加倍场景",
            "data": {
                "cards": "AAAA222XD3456",
                "is_landlord": False,
                "landlord_cards": "3456789T"
            }
        }
    ]

    for tc in test_cases_data:
        start = time.time()
        try:
            r = requests.post(f"{BASE_URL}/api/double", json=tc["data"], timeout=30)
            response_time = round((time.time() - start) * 1000, 2)

            case_result = {
                "name": tc["name"],
                "passed": False,
                "status_code": r.status_code,
                "response_time_ms": response_time
            }

            if r.status_code == 200:
                resp = r.json()
                case_result["response"] = resp
                # 验证响应结构
                required_fields = ["should_double", "should_super_double", "win_rate", "confidence"]
                has_all_fields = all(f in resp for f in required_fields)
                case_result["passed"] = has_all_fields
                case_result["validation"] = {
                    "has_required_fields": has_all_fields,
                    "should_double": resp.get("should_double"),
                    "should_super_double": resp.get("should_super_double"),
                    "win_rate": resp.get("win_rate")
                }
            else:
                case_result["error"] = r.text

            result.test_cases.append(case_result)
        except Exception as e:
            result.test_cases.append({
                "name": tc["name"],
                "passed": False,
                "error": str(e)
            })

    result.passed = all(c.get("passed", False) for c in result.test_cases)
    if result.test_cases:
        result.status_code = result.test_cases[0].get("status_code", 0)
        result.response_time_ms = max(c.get("response_time_ms", 0) for c in result.test_cases)

    return result


def generate_report(results: List[TestResult]) -> str:
    """生成测试报告"""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    report = []
    report.append("=" * 80)
    report.append("                    DouZero API 接口测试报告")
    report.append("=" * 80)
    report.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"服务地址: {BASE_URL}")
    report.append("")
    report.append("-" * 80)
    report.append("【测试概览】")
    report.append("-" * 80)
    report.append(f"  总接口数: {total}")
    report.append(f"  通过数量: {passed}")
    report.append(f"  失败数量: {failed}")
    report.append(f"  通过率:   {passed/total*100:.1f}%")
    report.append("")

    for i, result in enumerate(results, 1):
        status = "✅ PASS" if result.passed else "❌ FAIL"
        report.append("-" * 80)
        report.append(f"【{i}. {result.name}】{status}")
        report.append(f"    端点: {result.method} {result.endpoint}")
        report.append(f"    平均响应时间: {result.response_time_ms}ms")
        report.append("")

        for j, case in enumerate(result.test_cases, 1):
            case_status = "✅" if case.get("passed") else "❌"
            report.append(f"    测试用例 {j}: {case.get('name')} {case_status}")
            if "status_code" in case:
                report.append(f"        HTTP状态码: {case['status_code']}")
            if "response_time_ms" in case:
                report.append(f"        响应时间: {case['response_time_ms']}ms")
            if "validation" in case:
                report.append(f"        验证结果: {json.dumps(case['validation'], ensure_ascii=False)}")
            if "error" in case:
                report.append(f"        错误信息: {case['error']}")

        report.append("")

    report.append("=" * 80)
    report.append("                        测试结论")
    report.append("=" * 80)

    if failed == 0:
        report.append("  🎉 所有接口测试通过！API 服务运行正常。")
    else:
        report.append(f"  ⚠️  有 {failed} 个接口测试失败，请检查上述详情。")

    report.append("=" * 80)

    return "\n".join(report)


def main():
    print("开始测试 DouZero API 接口...")
    print()

    # 检查服务是否可用
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if r.status_code != 200:
            print(f"服务健康检查失败: HTTP {r.status_code}")
            return
    except Exception as e:
        print(f"无法连接到服务: {e}")
        return

    results = []

    # 测试各接口
    print("1. 测试健康检查接口...")
    results.append(test_health_endpoint())
    print("   完成")

    print("2. 测试出牌建议接口...")
    results.append(test_play_endpoint())
    print("   完成")

    print("3. 测试全量出牌建议接口...")
    results.append(test_actions_endpoint())
    print("   完成")

    print("4. 测试叫分建议接口...")
    results.append(test_bid_endpoint())
    print("   完成")

    print("5. 测试加倍建议接口...")
    results.append(test_double_endpoint())
    print("   完成")

    print()
    print("生成测试报告...")
    print()

    report = generate_report(results)
    print(report)

    # 保存报告到文件
    report_file = "test_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print()
    print(f"报告已保存到: {report_file}")


if __name__ == "__main__":
    main()
