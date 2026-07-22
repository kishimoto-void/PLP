"""
Energy Partition Monitor Module for PLP Kernel
================================================
ポテンシャルエネルギーを拘束 / Morse / Higgs に分割して監視するモジュール。
どの力がエネルギーを支配しているかを数字で可視化する。
"""

from __future__ import annotations
from typing import Optional, List
import logging
import numpy as np
from plp_kernel import (
    IAttachmentModule,
    ParticleLanguagePayload,
    PhysicsAxioms,
    DirectPairwiseSearch,
)

logger = logging.getLogger("PLP.EnergyPartition")


class EnergyPartitionMonitorModule(IAttachmentModule):
    """
    エネルギー内訳モニター。

    出力例:
      [EnergyPart] KE=0.51  Constr=0.42  Morse=-3.70  Higgs=0.13  Total=-2.64
                   |ΔE|=0.08  fraction_constr=0.10  fraction_morse=0.87
    """

    def __init__(
        self,
        axioms: Optional[PhysicsAxioms] = None,
        history_len: int = 32,
        log_every: int = 1,
    ):
        self.axi = axioms or PhysicsAxioms()
        self.neighbor = DirectPairwiseSearch()
        self.history_len = history_len
        self.log_every = log_every
        self._count = 0

        self.ke_hist: List[float] = []
        self.constr_hist: List[float] = []
        self.morse_hist: List[float] = []
        self.higgs_hist: List[float] = []

    def _compute_partitions(self, nu: np.ndarray) -> tuple[float, float, float, float]:
        """raw_nu からエネルギー内訳を再計算（モジュール独立性のため）"""
        X = nu[:, 0:3]
        V = nu[:, 3:6]
        M = nu[:, 6]
        C = nu[:, 7:9]

        # Kinetic
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
            np.sum(0.25 * M**4 - 0.5 * (self.axi.higgs_vev ** 2) * M**2)
        )

        # Morse
        _, r_ij = self.neighbor.compute_pairwise(X)
        exp_term = np.exp(-self.axi.morse_a * (r_ij - self.axi.morse_re))
        morse_val = self.axi.morse_de * ((1.0 - exp_term) ** 2 - 1.0)
        np.fill_diagonal(morse_val, 0.0)
        e_morse = 0.5 * float(np.sum(morse_val))

        return ke, e_constraint, e_morse, e_higgs

    def on_plp_payload(self, payload: ParticleLanguagePayload) -> None:
        self._count += 1
        if self._count % self.log_every != 0:
            return

        nu = payload.snapshot.raw_nu
        ke, e_c, e_m, e_h = self._compute_partitions(nu)
        total = ke + e_c + e_m + e_h
        delta_e = payload.energy.delta_energy

        # 割合（絶対値ベースで支配力を見る）
        abs_sum = abs(e_c) + abs(e_m) + abs(e_h) + 1e-12
        frac_c = abs(e_c) / abs_sum
        frac_m = abs(e_m) / abs_sum
        frac_h = abs(e_h) / abs_sum

        # 履歴
        self.ke_hist.append(ke)
        self.constr_hist.append(e_c)
        self.morse_hist.append(e_m)
        self.higgs_hist.append(e_h)
        if len(self.ke_hist) > self.history_len:
            self.ke_hist.pop(0)
            self.constr_hist.pop(0)
            self.morse_hist.pop(0)
            self.higgs_hist.pop(0)

        logger.info(
            f"  [EnergyPart] KE={ke:6.3f}  Constr={e_c:6.3f}  "
            f"Morse={e_m:7.3f}  Higgs={e_h:6.3f}  Total={total:7.3f}"
        )
        logger.info(
            f"               |ΔE|={abs(delta_e):.3f}  "
            f"frac(C/M/H)={frac_c:.2f}/{frac_m:.2f}/{frac_h:.2f}"
        )

    @property
    def recent_morse_dominance(self) -> float:
        """最近の Morse 寄与割合の平均"""
        if not self.morse_hist:
            return 0.0
        abs_sums = [
            abs(c) + abs(m) + abs(h) + 1e-12
            for c, m, h in zip(self.constr_hist, self.morse_hist, self.higgs_hist)
        ]
        fracs = [abs(m) / s for m, s in zip(self.morse_hist, abs_sums)]
        return float(np.mean(fracs))
