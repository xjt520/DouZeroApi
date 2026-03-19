from enum import Enum
from typing import List, Dict

# Card constants
REAL_CARD_TO_ENV = {
    '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
    '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12,
    'K': 13, 'A': 14, '2': 17, 'X': 20, 'D': 30
}

ENV_TO_REAL_CARD = {v: k for k, v in REAL_CARD_TO_ENV.items()}

ALL_ENV_CARDS = (
    [3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 7,
     8, 8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 11, 11, 11, 11, 12,
     12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 14, 17, 17, 17, 17, 20, 30]
)

class ActionType(Enum):
    PASS = "pass"
    SINGLE = "single"
    PAIR = "pair"
    TRIPLE = "triple"
    TRIPLE_SINGLE = "triple_single"
    TRIPLE_PAIR = "triple_pair"
    STRAIGHT = "straight"
    STRAIGHT_PAIR = "straight_pair"
    AIRPLANE = "airplane"
    AIRPLANE_SINGLE = "airplane_single"
    AIRPLANE_PAIR = "airplane_pair"
    FOUR_TWO_SINGLE = "four_two_single"
    FOUR_TWO_PAIR = "four_two_pair"
    BOMB = "bomb"
    ROCKET = "rocket"

class CardConverter:
    @staticmethod
    def real_to_env(cards: str) -> List[int]:
        result = []
        for c in cards:
            if c in REAL_CARD_TO_ENV:
                result.append(REAL_CARD_TO_ENV[c])
            else:
                raise ValueError(f"Unknown card: {c}")
        return sorted(result)

    @staticmethod
    def env_to_real(cards: List[int]) -> str:
        return ''.join([ENV_TO_REAL_CARD.get(c, '?') for c in cards])

class ActionTypeDetector:
    @staticmethod
    def detect(cards: List[int]) -> ActionType:
        if not cards:
            return ActionType.PASS
        
        n = len(cards)
        counter = {}
        for c in cards:
            counter[c] = counter.get(c, 0) + 1
        
        counts = sorted(counter.values(), reverse=True)
        unique_cards = len(counter)
        
        if n == 2 and 20 in cards and 30 in cards:
            return ActionType.ROCKET
        if n == 4 and counts == [4]:
            return ActionType.BOMB
        if n == 1:
            return ActionType.SINGLE
        if n == 2 and counts == [2]:
            return ActionType.PAIR
        if n == 3 and counts == [3]:
            return ActionType.TRIPLE
        if n == 4 and counts == [3, 1]:
            return ActionType.TRIPLE_SINGLE
        if n == 5 and counts == [3, 2]:
            return ActionType.TRIPLE_PAIR
        if n >= 5 and all(c == 1 for c in counts):
            sorted_cards = sorted(cards)
            if all(sorted_cards[i+1] - sorted_cards[i] == 1 for i in range(n-1)) and sorted_cards[-1] <= 14:
                return ActionType.STRAIGHT
        if n >= 6 and n % 2 == 0 and all(c == 2 for c in counts):
            unique_vals = sorted(counter.keys())
            if all(unique_vals[i+1] - unique_vals[i] == 1 for i in range(len(unique_vals)-1)) and unique_vals[-1] <= 14:
                return ActionType.STRAIGHT_PAIR
        if n >= 6:
            triples = [k for k, v in counter.items() if v == 3]
            if len(triples) >= 2:
                triples_sorted = sorted(triples)
                is_consecutive = all(triples_sorted[i+1] - triples_sorted[i] == 1 for i in range(len(triples_sorted)-1))
                if is_consecutive and triples_sorted[-1] <= 14:
                    triple_count = len(triples)
                    remaining = n - triple_count * 3
                    if remaining == 0:
                        return ActionType.AIRPLANE
                    elif remaining == triple_count:
                        return ActionType.AIRPLANE_SINGLE
                    elif remaining == triple_count * 2:
                        return ActionType.AIRPLANE_PAIR
        if n == 6 and 4 in counts:
            return ActionType.FOUR_TWO_SINGLE
        if n == 8 and counts == [4, 2, 2]:
            return ActionType.FOUR_TWO_PAIR
        
        return ActionType.PASS
