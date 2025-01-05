from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class Error(BaseModel):
    code: str
    message: str


class Point(BaseModel):
    x: float
    y: float


class GamutPoint(BaseModel):
    x: float
    y: float


class Gamut(BaseModel):
    red: GamutPoint
    green: GamutPoint
    blue: GamutPoint


class Color(BaseModel):
    xy: Point
    gamut: Optional[Gamut] = None
    gamut_type: Optional[str] = None  # One of "A", "B", "C", "other"


class MirekSchema(BaseModel):
    mirek_minimum: int
    mirek_maximum: int


class ColorTemperature(BaseModel):
    mirek: Optional[int] = None
    mirek_valid: Optional[bool] = None
    mirek_schema: Optional[MirekSchema] = None


class Dimming(BaseModel):
    brightness: float
    min_dim_level: Optional[float] = None


class On(BaseModel):
    on: bool


class GradientPointGet(BaseModel):
    color: Color


class Gradient(BaseModel):
    points: List[GradientPointGet]
    points_capable: int
    mode: str  # One of "interpolated_palette", "interpolated_palette_mirrored", "random_pixelated"
    mode_values: List[str]
    pixel_count: Optional[int] = None


class Dynamics(BaseModel):
    status: str  # One of "dynamic_palette", "none"
    status_values: List[str]
    speed: float
    speed_valid: bool


class Alert(BaseModel):
    action_values: List[str]  # AlertEffectType


class SignalingStatus(BaseModel):
    signal: Optional[str] = None  # One of "no_signal", "on_off", "on_off_color", "alternating"
    estimated_end: Optional[datetime] = None


class Signaling(BaseModel):
    signal_values: Optional[List[str]] = None
    status: Optional[SignalingStatus] = None


class Effects(BaseModel):
    status: str  # One of "prism", "opal", "glisten", "sparkle", "fire", "candle", "no_effect"
    status_values: List[str]
    effect_values: List[str]


class TimedEffects(BaseModel):
    status: str  # One of "sunrise", "sunset", "no_effect"
    status_values: List[str]
    effect_values: List[str]


class PowerupOn(BaseModel):
    mode: str  # One of "on", "toggle", "previous"
    on: Optional[On] = None


class PowerupDimming(BaseModel):
    mode: str  # One of "dimming", "previous"
    dimming: Optional[Dimming] = None


class PowerupColorTemperature(BaseModel):
    mode: str  # One of "color_temperature", "color", "previous"
    color_temperature: Optional[ColorTemperature] = None


class PowerupColor(BaseModel):
    mode: str  # One of "color_temperature", "color", "previous"
    color: Optional[Color] = None


class Powerup(BaseModel):
    preset: str  # One of "safety", "powerfail", "last_on_state", "custom"
    configured: bool
    on: PowerupOn
    dimming: Optional[PowerupDimming] = None
    color_temperature: Optional[PowerupColorTemperature] = None
    color: Optional[PowerupColor] = None


class Metadata(BaseModel):
    name: Optional[str] = None
    archetype: Optional[str] = None
    fixed_mired: Optional[int] = None
    function: str = "unknown"


class Owner(BaseModel):
    rid: str
    rtype: str


class HueLight(BaseModel):
    type: str  # "light"
    id: str
    id_v1: Optional[str] = None
    owner: Owner
    on: On
    dimming: Optional[Dimming] = None
    color_temperature: Optional[ColorTemperature] = None
    color: Optional[Color] = None
    metadata: Metadata
    archetype: Optional[str] = "unknown"  # Deprecated
    fixed_mired: Optional[int] = None
    function: str = "unknown"  # One of "functional", "decorative", "mixed", "unknown"
    product_data: Optional[Metadata] = None
    dynamics: Optional[Dynamics] = None
    alert: Optional[Alert] = None
    signaling: Optional[Signaling] = None
    effects: Optional[Effects] = None
    timed_effects: Optional[TimedEffects] = None
    powerup: Optional[Powerup] = None


class Response(BaseModel):
    errors: List[Error]
    description: str
    data: List[HueLight]


class ErrorResponse(BaseModel):
    errors: List[Error]
    description: str
