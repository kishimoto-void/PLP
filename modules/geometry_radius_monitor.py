"""
Geometry / Radius Monitor Module for PLP Kernel
================================================
半径・幾何に関する統計を監視するアタッチメントモジュール。
v10.2 で半径 std ≈ 0.017 まで詰めた直後の検証用に設計。

改良点:
- GeometrySnapshot 構造体で Telemetry / Dashboard 共有を容易に
- deque による O(1) 履歴管理
- 質量加重 COM（M を重みとして使用）
- get_recent_statistics() で WebUI / RL 向け統計を提供
"""

from __future__ import annotations
from collections import deque
from dataclasses import dataclass, asdict
from typing import Optional, Dict
import logging
import numpy as np
from plp_kernel import (
    IAttachmentModule,
    ParticleLanguagePayload,
    PhysicsAxioms,
)

logger = logging.getLogger("PLP.Geometry")


@dataclass(frozen=True)
class GeometrySnapshot:
    """幾何・統計情報スナップショット構造体（Telemetry / Dashboard 共有用）"""

    mean_r: float
    std_r: float
    r_min: float
    r_max: float
    skew: float
    kurt: float
    com_norm: float
    e_constraint: float
    corr_r_dev: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


class GeometryRadiusMonitorModule(IAttachmentModule):
    """
    PLP Kernel 観測（Observer）モジュール：半径・幾何統計モニター。

    ・半径分布（mean / std / range / skew / kurt）の精密監視（v10.2 検証用）
    ・質量加重重心（COM）の漂流（Drift）追跡
    ・拘束条件（Constraint）との相関分析
    ・Telemetry / Dashboard / RL 向け統計データの集約提供
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

        # O(1) 履歴管理用 deque
        self.mean_r_hist: deque[float] = deque(maxlen=history_len)
        self.std_r_hist: deque[float] = deque(maxlen=history_len)
        self.com_norm_hist: deque[float] = deque(maxlen=history_len)
        self.corr_hist: deque[float] = deque(maxlen=history_len)

        self._last_snapshot: Optional[GeometrySnapshot] = None

    def compute_geometry(self, nu: np.ndarray) -> GeometrySnapshot:
        """raw_nu から幾何統計パケットを生成"""
        if nu.shape[0] == 0:
            return GeometrySnapshot(
                mean_r=0.0,
                std_r=0.0,
                r_min=0.0,
                r_max=0.0,
                skew=0.0,
                kurt=0.0,
                com_norm=0.0,
                e_constraint=0.0,
                corr_r_dev=0.0,
            )

        X = nu[:, 0:3]
        M = nu[:, 6]
        C = nu[:, 7:9]

        # --- 半径統計 ---
        radii = np.linalg.norm(X, axis=1)
        mean_r = float(np.mean(radii))
        std_r = float(np.std(radii))
        r_min, r_max = float(np.min(radii)), float(np.max(radii))

        # 歪度・尖度
        if std_r > 1e-9:
            centered = (radii - mean_r) / std_r
            skew = float(np.mean(centered**3))
            kurt = float(np.mean(centered**4) - 3.0)  # excess kurtosis
        else:
            skew, kurt = 0.0, 0.0

        # --- 質量加重重心 (Center of Mass) ---
        # M は Higgs 型マージン場だが、重みとして利用
        total_mass = float(np.sum(M))
        if total_mass > 1e-12:
            com = np.sum(X * M[:, np.newaxis], axis=0) / total_mass
        else:
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
        e_constraint = 0.5 * self.axi.mu_constraint * float(np.sum(radial_dev**2))

        abs_dev = np.abs(radial_dev)
        if std_r > 1e-9 and np.std(abs_dev) > 1e-9:
            corr = float(np.corrcoef(radii, abs_dev)[0, 1])
        else:
            corr = 0.0

        return GeometrySnapshot(
            mean_r=mean_r,
            std_r=std_r,
            r_min=r_min,
            r_max=r_max,
            skew=skew,
            kurt=kurt,
            com_norm=com_norm,
            e_constraint=e_constraint,
            corr_r_dev=corr,
        )

    def on_plp_payload(self, payload: ParticleLanguagePayload) -> None:
        self._count += 1
        if self._count % self.log_every != 0:
            return

        nu = payload.snapshot.raw_nu
        snap = self.compute_geometry(nu)
        self._last_snapshot = snap

        # 履歴更新
        self.mean_r_hist.append(snap.mean_r)
        self.std_r_hist.append(snap.std_r)
        self.com_norm_hist.append(snap.com_norm)
        self.corr_hist.append(snap.corr_r_dev)

        logger.info(
            f"  [Geometry] mean_r={snap.mean_r:.4f}  std_r={snap.std_r:.4f}  "
            f"range=[{snap.r_min:.3f},{snap.r_max:.3f}]  skew={snap.skew:+.2f}  kurt={snap.kurt:+.2f}"
        )
        logger.info(
            f"             COM_norm={snap.com_norm:.4f}  e_constraint={snap.e_constraint:.3f}  "
            f"corr(r,|dev|)={snap.corr_r_dev:+.3f}"
        )

    @property
    def recent_std_r(self) -> float:
        """直近の半径標準偏差（std_r）の平均（目標値 ≈ 0.017 の到達確認用）"""
        if not self.std_r_hist:
            return 0.0
        return float(np.mean(self.std_r_hist))

    @property
    def recent_com_drift(self) -> float:
        """直近の重心（COM）漂流距離の平均"""
        if not self.com_norm_hist:
            return 0.0
        return float(np.mean(self.com_norm_hist))

    @property
    def last_snapshot(self) -> Optional[GeometrySnapshot]:
        """直近の幾何構造スナップショットパケット"""
        return self._last_snapshot

    def get_recent_statistics(self) -> Dict[str, float]:
        """
        WebUI / Dashboard / RL 向けに、直近ウィンドウの幾何統計量を抽出
        """
        if not self.mean_r_hist:
            return {}

        return {
            "mean_r": float(np.mean(self.mean_r_hist)),
            "std_r": float(np.mean(self.std_r_hist)),
            "std_r_stability": float(np.std(self.std_r_hist)),  # std_r 自体のブレ
            "mean_com_drift": float(np.mean(self.com_norm_hist)),
            "mean_corr_r_dev": float(np.mean(self.corr_hist)),
        }
