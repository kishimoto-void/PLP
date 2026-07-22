"""
Energy Partition Monitor Module for PLP Kernel
================================================
ポテンシャルエネルギーを拘束 / Morse / Higgs に分割して監視するモジュール。
どの力がエネルギーを支配しているかを数字で可視化する。

改良点:
- EnergyBreakdown 構造体で Telemetry / Dashboard 共有を容易に
- deque による O(1) 履歴管理
- エネルギー計算関数の注入対応（二重管理防止）
- get_recent_statistics() で WebUI / RL 向け統計を提供
"""

from __future__ import annotations
from collections import deque
from dataclasses import dataclass, asdict
from typing import Optional, Tuple, Dict, Any, Callable
import logging
import numpy as np
from plp_kernel import (
    IAttachmentModule,
    ParticleLanguagePayload,
    PhysicsAxioms,
    DirectPairwiseSearch,
)

logger = logging.getLogger("PLP.EnergyPartition")


@dataclass(frozen=True)
class EnergyBreakdown:
    """エネルギー内訳のスナップショット構造体（Telemetry / Dashboard 共有用）"""

    ke: float
    e_constraint: float
    e_morse: float
    e_higgs: float
    total: float
    frac_constraint: float
    frac_morse: float
    frac_higgs: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


class EnergyPartitionMonitorModule(IAttachmentModule):
    """
    PLP Kernel 観測（Observer）モジュール：エネルギー内訳モニター。

    ・Payloadを受け取り、物理状態の分解解析と統計データの非同期提供を行う
    ・Telemetry / WebUI / RL / Dashboard 連携用パケットの生成
    """

    def __init__(
        self,
        axioms: Optional[PhysicsAxioms] = None,
        history_len: int = 32,
        log_every: int = 1,
        energy_calc_fn: Optional[
            Callable[[np.ndarray, PhysicsAxioms], Tuple[float, float, float, float]]
        ] = None,
    ):
        self.axi = axioms or PhysicsAxioms()
        self.neighbor = DirectPairwiseSearch()
        self.history_len = history_len
        self.log_every = log_every
        self._count = 0

        # 物理計算エンジンの注入（二重管理を防止する場合に使用）
        self._energy_calc_fn = energy_calc_fn

        # 履歴保持用 deque (O(1))
        self.ke_hist: deque[float] = deque(maxlen=history_len)
        self.constr_hist: deque[float] = deque(maxlen=history_len)
        self.morse_hist: deque[float] = deque(maxlen=history_len)
        self.higgs_hist: deque[float] = deque(maxlen=history_len)
        self.morse_dominance_hist: deque[float] = deque(maxlen=history_len)

        self._last_breakdown: Optional[EnergyBreakdown] = None

    def _default_compute_partitions(
        self, nu: np.ndarray
    ) -> Tuple[float, float, float, float]:
        """モジュール内ローカル計算（フォールバック用）

        Note: KE はカーネル本体 (PayloadBuilder) と一致させるため
              0.5 * sum(V**2) を使用（M は Higgs 場であり質量ではない）
        """
        if nu.shape[0] == 0:
            return 0.0, 0.0, 0.0, 0.0

        X = nu[:, 0:3]
        V = nu[:, 3:6]
        M = nu[:, 6]
        C = nu[:, 7:9]

        # Kinetic（カーネル本体と定義を揃える）
        ke = 0.5 * float(np.sum(V ** 2))

        # Constraint
        clock_phase = np.arctan2(C[:, 1], C[:, 0])
        R_i = (
            self.axi.r0_base
            + self.axi.r_phase_amp * np.cos(clock_phase * 2.0)
            + self.axi.r_margin_coef * (M - self.axi.higgs_vev)
        )
        dists = np.linalg.norm(X, axis=1)
        radial_dev = dists - R_i
        e_constraint = 0.5 * self.axi.mu_constraint * float(np.sum(radial_dev ** 2))

        # Higgs
        e_higgs = self.axi.higgs_lambda * float(
            np.sum(0.25 * (M ** 4) - 0.5 * (self.axi.higgs_vev ** 2) * (M ** 2))
        )

        # Morse
        _, r_ij = self.neighbor.compute_pairwise(X)
        exp_term = np.exp(-self.axi.morse_a * (r_ij - self.axi.morse_re))
        morse_val = self.axi.morse_de * ((1.0 - exp_term) ** 2 - 1.0)
        np.fill_diagonal(morse_val, 0.0)
        e_morse = 0.5 * float(np.sum(morse_val))

        return ke, e_constraint, e_morse, e_higgs

    def compute_breakdown(self, nu: np.ndarray) -> EnergyBreakdown:
        """エネルギー内訳パケットの生成"""
        if self._energy_calc_fn is not None:
            ke, e_c, e_m, e_h = self._energy_calc_fn(nu, self.axi)
        else:
            ke, e_c, e_m, e_h = self._default_compute_partitions(nu)

        total = ke + e_c + e_m + e_h
        abs_sum = abs(e_c) + abs(e_m) + abs(e_h) + 1e-12

        return EnergyBreakdown(
            ke=ke,
            e_constraint=e_c,
            e_morse=e_m,
            e_higgs=e_h,
            total=total,
            frac_constraint=abs(e_c) / abs_sum,
            frac_morse=abs(e_m) / abs_sum,
            frac_higgs=abs(e_h) / abs_sum,
        )

    def on_plp_payload(self, payload: ParticleLanguagePayload) -> None:
        self._count += 1
        if self._count % self.log_every != 0:
            return

        nu = payload.snapshot.raw_nu
        bd = self.compute_breakdown(nu)
        self._last_breakdown = bd
        delta_e = payload.energy.delta_energy

        # 履歴更新
        self.ke_hist.append(bd.ke)
        self.constr_hist.append(bd.e_constraint)
        self.morse_hist.append(bd.e_morse)
        self.higgs_hist.append(bd.e_higgs)
        self.morse_dominance_hist.append(bd.frac_morse)

        logger.info(
            f"  [EnergyPart] KE={bd.ke:6.3f}  Constr={bd.e_constraint:6.3f}  "
            f"Morse={bd.e_morse:7.3f}  Higgs={bd.e_higgs:6.3f}  Total={bd.total:7.3f}"
        )
        logger.info(
            f"               |ΔE|={abs(delta_e):.3f}  "
            f"frac(C/M/H)={bd.frac_constraint:.2f}/{bd.frac_morse:.2f}/{bd.frac_higgs:.2f}"
        )

    @property
    def recent_morse_dominance(self) -> float:
        """最近の Morse 寄与割合の平均"""
        if not self.morse_dominance_hist:
            return 0.0
        return float(np.mean(self.morse_dominance_hist))

    @property
    def last_breakdown(self) -> Optional[EnergyBreakdown]:
        """直近に計算されたエネルギー内訳パケット"""
        return self._last_breakdown

    def get_recent_statistics(self) -> Dict[str, float]:
        """
        WebUI / Unity / Dashboard / RL 向けに、直近ウィンドウの各種統計量を抽出
        """
        if not self.ke_hist:
            return {}

        totals = [
            k + c + m + h
            for k, c, m, h in zip(
                self.ke_hist, self.constr_hist, self.morse_hist, self.higgs_hist
            )
        ]

        return {
            "mean_ke": float(np.mean(self.ke_hist)),
            "mean_constraint": float(np.mean(self.constr_hist)),
            "mean_morse": float(np.mean(self.morse_hist)),
            "mean_higgs": float(np.mean(self.higgs_hist)),
            "mean_total": float(np.mean(totals)),
            "std_total": float(np.std(totals)),
            "mean_morse_dominance": float(np.mean(self.morse_dominance_hist)),
        }
