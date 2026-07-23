"""
PLP Core — Clock v1.0 (strict)
==============================
共通時間の記述のみ。意味解釈・スケジューラ・AI は持たない。

役割:
  - tick / delta_time / phase / frequency
  - 全モジュールの同期基準

非役割:
  - イベント発火の意味付け
  - 物理積分そのもの
  - リアルタイム OS スケジューリング

共通 Core インターフェース:
  schema / version
  check_invariants() / is_valid()
  copy() / to_dict() / from_dict()

不変条件:
  T1. id は非空 ClockID
  T2. tick >= 0（整数）
  T3. delta_time > 0 and finite
  T4. frequency > 0 and finite
  T5. phase は finite
  T6. time >= 0 and finite（累積時間）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional
from uuid import uuid4
import numpy as np


CLOCK_VERSION = "1.0"
CLOCK_SCHEMA = "plp.core.clock/1.0"


class ClockID(str):
    """時計識別子。空文字禁止。"""

    __slots__ = ()

    def __new__(cls, value: str) -> "ClockID":
        if not isinstance(value, str):
            raise TypeError(f"ClockID requires str, got {type(value).__name__}")
        value = value.strip()
        if not value:
            raise ValueError("ClockID must be non-empty")
        return super().__new__(cls, value)

    @classmethod
    def new(cls) -> "ClockID":
        return cls(str(uuid4()))


def _validate_positive_finite(name: str, value: float) -> float:
    v = float(value)
    if not np.isfinite(v):
        raise ValueError(f"{name} must be finite")
    if v <= 0.0:
        raise ValueError(f"{name} must be positive")
    return v


def _validate_nonnegative_finite(name: str, value: float) -> float:
    v = float(value)
    if not np.isfinite(v):
        raise ValueError(f"{name} must be finite")
    if v < 0.0:
        raise ValueError(f"{name} must be >= 0")
    return v


@dataclass(slots=True)
class Clock:
    """
    共通時間の最小記述。

    - id         : ClockID
    - tick       : 離散ステップ（0 起点）
    - delta_time : 1 tick あたりの時間幅
    - frequency  : 1 / delta_time（整合を取る）
    - phase      : 位相スカラー（同期用）
    - time       : 累積時間（通常 tick * delta_time）
    - paused     : 停止フラグ（意味解釈なし）
    - metadata   : opaque
    """

    id: ClockID = field(default_factory=ClockID.new)
    tick: int = 0
    delta_time: float = 0.0155
    frequency: float = field(init=False, default=0.0)
    phase: float = 0.0
    time: float = 0.0
    paused: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.id, ClockID):
            self.id = ClockID(str(self.id))

        if not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("tick must be int >= 0")

        dt = _validate_positive_finite("delta_time", self.delta_time)
        self.delta_time = dt
        self.frequency = 1.0 / dt

        ph = float(self.phase)
        if not np.isfinite(ph):
            raise ValueError("phase must be finite")
        self.phase = ph

        # time 未設定相当（0）なら tick から再計算可
        t = _validate_nonnegative_finite("time", self.time)
        self.time = t

        if not isinstance(self.paused, bool):
            raise TypeError("paused must be bool")

        md: dict[str, Any] = {}
        for k, v in dict(self.metadata).items():
            if not isinstance(k, str):
                raise TypeError("metadata keys must be str")
            md[k] = v
        self.metadata = md

    # ------------------------------------------------------------------
    # 共通インターフェース
    # ------------------------------------------------------------------

    @property
    def schema(self) -> str:
        return CLOCK_SCHEMA

    @property
    def version(self) -> str:
        return CLOCK_VERSION

    def check_invariants(self) -> None:
        if not isinstance(self.id, ClockID) or not str(self.id):
            raise ValueError("invalid id")
        if not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("tick must be int >= 0")
        _validate_positive_finite("delta_time", self.delta_time)
        _validate_positive_finite("frequency", self.frequency)
        if abs(self.frequency * self.delta_time - 1.0) > 1e-9:
            raise ValueError("frequency must equal 1/delta_time")
        if not np.isfinite(self.phase):
            raise ValueError("phase must be finite")
        _validate_nonnegative_finite("time", self.time)
        if not isinstance(self.paused, bool):
            raise TypeError("paused must be bool")

    def is_valid(self) -> bool:
        try:
            self.check_invariants()
            return True
        except (TypeError, ValueError):
            return False

    def copy(self) -> "Clock":
        c = Clock(
            id=ClockID(str(self.id)),
            tick=self.tick,
            delta_time=self.delta_time,
            phase=self.phase,
            time=self.time,
            paused=self.paused,
            metadata=dict(self.metadata),
        )
        return c

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CLOCK_SCHEMA,
            "version": CLOCK_VERSION,
            "id": str(self.id),
            "tick": self.tick,
            "delta_time": self.delta_time,
            "frequency": self.frequency,
            "phase": self.phase,
            "time": self.time,
            "paused": self.paused,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Clock":
        return cls(
            id=ClockID(str(data["id"])) if "id" in data else ClockID.new(),
            tick=int(data.get("tick", 0)),
            delta_time=float(data.get("delta_time", 0.0155)),
            phase=float(data.get("phase", 0.0)),
            time=float(data.get("time", 0.0)),
            paused=bool(data.get("paused", False)),
            metadata=dict(data.get("metadata") or {}),
        )

    # ------------------------------------------------------------------
    # 時間操作（意味を付けない。ただ進める）
    # ------------------------------------------------------------------

    def step(self, n: int = 1) -> "Clock":
        """
        n tick 進めた新しい Clock を返す（非破壊）。
        paused の場合は同一状態を copy して返す。
        """
        if not isinstance(n, int) or n < 0:
            raise ValueError("n must be int >= 0")
        if self.paused or n == 0:
            return self.copy()

        new_tick = self.tick + n
        new_time = self.time + self.delta_time * n
        # phase は 2π で正規化せず、生の加算のみ（解釈は上位）
        new_phase = self.phase + self.delta_time * n
        return Clock(
            id=ClockID(str(self.id)),
            tick=new_tick,
            delta_time=self.delta_time,
            phase=new_phase,
            time=new_time,
            paused=self.paused,
            metadata=dict(self.metadata),
        )

    def with_delta_time(self, delta_time: float) -> "Clock":
        """刻み幅を変更した新しい Clock（tick/time は維持）。"""
        return Clock(
            id=ClockID(str(self.id)),
            tick=self.tick,
            delta_time=delta_time,
            phase=self.phase,
            time=self.time,
            paused=self.paused,
            metadata=dict(self.metadata),
        )

    def with_paused(self, paused: bool) -> "Clock":
        c = self.copy()
        c.paused = bool(paused)
        return c

    def sync_time_from_tick(self) -> "Clock":
        """time = tick * delta_time に揃える。"""
        return Clock(
            id=ClockID(str(self.id)),
            tick=self.tick,
            delta_time=self.delta_time,
            phase=self.phase,
            time=float(self.tick) * self.delta_time,
            paused=self.paused,
            metadata=dict(self.metadata),
        )

    @classmethod
    def create(
        cls,
        *,
        delta_time: float = 0.0155,
        clock_id: Optional[str] = None,
        phase: float = 0.0,
    ) -> "Clock":
        return cls(
            id=ClockID(clock_id) if clock_id else ClockID.new(),
            tick=0,
            delta_time=delta_time,
            phase=phase,
            time=0.0,
            paused=False,
        )


if __name__ == "__main__":
    c = Clock.create(delta_time=0.0155, clock_id="clock-main")
    assert c.is_valid()
    c2 = c.step(10)
    assert c2.tick == 10
    assert abs(c2.time - 10 * 0.0155) < 1e-12
    assert abs(c2.frequency - 1.0 / 0.0155) < 1e-9

    d = c2.to_dict()
    c3 = Clock.from_dict(d)
    assert c3.tick == 10
    assert c3.schema == CLOCK_SCHEMA

    paused = c2.with_paused(True).step(5)
    assert paused.tick == c2.tick

    print("schema:", c.schema, "version:", c.version)
    print("Clock v1.0 ok")
