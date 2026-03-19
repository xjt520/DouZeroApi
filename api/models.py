from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional

class PlayRequest(BaseModel):
    """Request for getting best play action"""
    position: str = Field(
        ..., 
        description="Player position: landlord, landlord_up, or landlord_down"
    )
    my_cards: str = Field(
        ..., 
        description="Your hand cards, e.g. '3456789TJQKA2XD'"
    )
    played_cards: Dict[str, str] = Field(
        default_factory=lambda: {"landlord": "", "landlord_up": "", "landlord_down": ""},
        description="Cards played by each position"
    )
    last_moves: List[str] = Field(
        default_factory=list,
        description="Recent moves (last 2-3)"
    )
    landlord_cards: str = Field(
        default="",
        description="Three landlord cards (底牌)"
    )
    cards_left: Optional[Dict[str, int]] = Field(
        default=None,
        description="Cards left for each position, e.g. {\"landlord\": 15, \"landlord_up\": 10, \"landlord_down\": 8}"
    )
    bomb_count: int = Field(
        default=0,
        description="Number of bombs played so far"
    )
    bid_info: Optional[List[List[float]]] = Field(
        default=None,
        description="4x3 matrix encoding bidding round outcomes"
    )
    multiply_info: Optional[List[float]] = Field(
        default=None,
        description="3-element vector encoding doubling state [base, landlord_mul, farmer_mul]"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "position": "landlord",
                "my_cards": "3456789TJQKA2XD",
                "played_cards": {"landlord": "", "landlord_up": "KK", "landlord_down": ""},
                "last_moves": ["KK"],
                "landlord_cards": "22D"
            }
        }
    )

class ActionResponse(BaseModel):
    """Response for a card action"""
    cards: str = Field(description="Cards to play (empty string for pass)")
    win_rate: float = Field(description="Predicted win rate (0-1)")
    action_type: str = Field(description="Type of action")
    confidence: float = Field(default=0.0, description="Model confidence")
    is_pass: bool = Field(description="Whether this is a pass action")
    is_bomb: bool = Field(description="Whether this is a bomb")

class ActionsResponse(BaseModel):
    """Response for all actions"""
    best_action: ActionResponse
    actions: List[ActionResponse]
    total_count: int

class BidRequest(BaseModel):
    """Request for bid evaluation"""
    cards: str = Field(
        ..., 
        description="Hand cards (17 cards before seeing landlord cards)"
    )
    threshold: float = Field(
        default=0.5,
        description="Win rate threshold for bidding"
    )

class BidResponse(BaseModel):
    """Response for bid evaluation"""
    should_bid: bool
    win_rate: float
    farmer_win_rate: float
    confidence: float

class DoubleRequest(BaseModel):
    """Request for double evaluation"""
    cards: str = Field(description="Current hand cards")
    is_landlord: bool = Field(description="Whether player is landlord")
    landlord_cards: str = Field(
        default="",
        description="Three landlord cards"
    )
    position: Optional[str] = Field(
        default=None,
        description="Player position: landlord_up or landlord_down (for farmers only)"
    )

class DoubleResponse(BaseModel):
    """Response for double evaluation"""
    should_double: bool
    should_super_double: bool
    win_rate: float
    confidence: float

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    agent_initialized: bool

class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: str
