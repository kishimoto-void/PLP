"""
Geometry / Radius Monitor Module for PLP Kernel
================================================
半径・幾何に関する統計を監視するアタッチメントモジュール。
v10.2 で半径 std ≈ 0.017 まで詰めた直後の検証用に設計。
"""

from __future__ import annotations
from typing import Optional, List
import logging
import numpy as np
from plp_kernel import (
    IAttachmentModule,
    ParticleLanguagePayload,
    PhysicsAxioms,
)

logger = logging.getLogger("PLP.Geometry")


class GeometryRadiusMonitorModule(IAttachmentModule):
    """
    半径分布・COM・拘束との関係を監視するモジュール。

    出力例:
      [Geometry] mean_r=1.689  std_r=0.017  range=[1.66,1.73]
                 skew=0.12  kurt=-0.45  COM_norm=0.031
                 e_constraint≈0.42  corr(r, |dev|)≈0.91
    """

    def __init__(
        self,
        axioms: Optional[PhysicsAxioms] = None,
        history_len: int = 32,
        log_every: int = 1,
    ):
        self.axi = axioms or PhysicsAxioms()
        self.history_len = history_len
        self.log_every = log_every
        self._count = 0

        # 履歴（簡易）
        self.mean_r_hist: List[float] = []
        self.std_r_hist: List[float] = []
        self.com_norm_hist: List[float] = []

    def on_plp_payload(self, payload: ParticleLanguagePayload) -> None:
        self._count += 1
        if self._count % self.log_every != 0:
            return

        nu = payload.snapshot.raw_nu
        X = nu[:, 0:3]
        M = nu[:, 6]
        C = nu[:, 7:9]

        # --- 半径統計 ---
        radii = np.linalg.norm(X, axis=1)
        mean_r = float(np.mean(radii))
        std_r = float(np.std(radii))
        r_min, r_max = float(np.min(radii)), float(np.max(radii))

        # 歪度・尖度（簡易）
        if std_r > 1e-9:
            centered = (radii - mean_r) / std_r
            skew = float(np.mean(centered ** 3))
            kurt = float(np.mean(centered ** 4) - 3.0)  # excess kurtosis
        else:
            skew, kurt = 0.0, 0.0

        # --- COM ---
        com = np.mean(X, axis=0)
        com_norm = float(np.linalg.norm(com))

        # --- 拘束エネルギーと相関 ---
        clock_phase = np.arctan2(C[:, 1], C[:, 0])
        R_i = (
            self.axi.r0_base
            + self.axi.r_phase_amp * np.cos(clock_phase * 2.0)
            + self.axi.r_margin_coef * (M - self.axi.higgs_vev)
        )
        radial_dev = radii - R_i
        e_constraint = 0.5 * self.axi.mu_constraint * float(np.sum(radial_dev ** 2))

        # 半径と |dev| の相関（拘束の効き具合の目安）
        if std_r > 1e-9 and np.std(np.abs(radial_dev)) > 1e-9:
            corr = float(np.corrcoef(radii, np.abs(radial_dev))[0, 1])
        else:
            corr = 0.0

        # 履歴更新
        self.mean_r_hist.append(mean_r)
        self.std_r_hist.append(std_r)
        self.com_norm_hist.append(com_norm)
        if len(self.mean_r_hist) > self.history_len:
            self.mean_r_hist.pop(0)
            self.std_r_hist.pop(0)
            self.com_norm_hist.pop(0)

        logger.info(
            f"  [Geometry] mean_r={mean_r:.4f}  std_r={std_r:.4f}  "
            f"range=[{r_min:.3f},{r_max:.3f}]  skew={skew:+.2f}  kurt={kurt:+.2f}"
        )
        logger.info(
            f"             COM_norm={com_norm:.4f}  e_constraint={e_constraint:.3f}  "
            f"corr(r,|dev|)={corr:+.3f}"
        )

    # 便利プロパティ（外部から履歴を見る用）
    @property
    def recent_std_r(self) -> float:
        return float(np.mean(self.std_r_hist)) if self.std_r_hist else 0.0

    @property
    def recent_com_drift(self) -> float:
        return float(np.mean(self.com_norm_hist)) if self.com_norm_hist else 0.0
