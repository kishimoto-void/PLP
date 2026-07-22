#!/usr/bin/env python3
"""
Particle Language Protocol (PLP) Kernel v10.2
=========================================================
【Axiomatic, Pipeline-Oriented Production Kernel】
Numerically Faithful Edition (radius std ≈ 0.017 target)

確定パラメータ（実験で半径 std 0.02 台 + エネルギー安定を達成）:
  mu_constraint=18.0, morse_de=0.085, r_phase_amp=0.09, r_margin_coef=0.13
  gamma_base=2.5, force_clip=13.5, dt=0.0155, temp_env=0.0065
"""

from dataclasses import dataclass
from enum import Enum, auto
import json
import logging
import math
from typing import Any, Dict, List, Optional, Protocol, Tuple, Sequence
import numpy as np

logger = logging.getLogger("PLP")


# =============================================================================
# 1. 公理層
# =============================================================================
@dataclass(frozen=True)
class PhysicsAxioms:
  """物理空間における公理パラメータ（数字的忠実性・半径安定優先）"""

  n_particles: int = 14
  dim_per_particle: int = 9

  mu_constraint: float = 18.0
  r0_base: float = 1.70
  r_phase_amp: float = 0.09
  r_margin_coef: float = 0.13

  morse_de: float = 0.085
  morse_a: float = 1.25
  morse_re: float = 0.95

  higgs_lambda: float = 0.8
  higgs_vev: float = 0.35
  d_margin: float = 0.20
  mobility_margin: float = 0.09

  clock_omega: float = 1.3333
  sl_alpha: float = 5.0

  def validate(self) -> None:
    if self.n_particles < 2:
      raise ValueError("n_particles must be >= 2")
    if self.dim_per_particle != 9:
      raise ValueError("dim_per_particle is fixed to 9 for current protocol")
    if self.mu_constraint <= 0 or self.morse_de <= 0:
      raise ValueError("force scales must be positive")
    if not (0.0 < self.higgs_vev < 2.0):
      raise ValueError("higgs_vev out of reasonable range")


@dataclass(frozen=True)
class NumericalConfig:
  """数値計算および観測パラメータ"""

  temp_env: float = 0.0065
  dt: float = 0.0155

  min_obs_interval: int = 8
  max_obs_interval: int = 40
  sensitivity_eta: float = 12.0
  ema_alpha: float = 0.30


@dataclass(frozen=True)
class ObservationAxioms:
  """観測・相転移・異常検知の公理（新しい小さいエネルギー尺度に合わせた）"""

  rate_stable_to_pert: float = 0.008
  rate_pert_to_trans: float = 0.012
  rate_to_relax: float = 0.005
  rate_relax_to_stable: float = 0.0025
  rate_relax_to_pert: float = 0.012

  # |ΔE| が mean≈0.09 / max≈0.24 の世界なので閾値を下げる
  energy_anomaly_threshold: float = 0.6

  energy_consistency_tol: float = 1e-6


# =============================================================================
# 2. PLP 言語パケット群
# =============================================================================
@dataclass(frozen=True)
class PhysicsSnapshot:
  center_of_mass: List[float]
  mean_radius: float
  mean_clock_phase: float
  mean_margin: float
  raw_nu: np.ndarray

  def __post_init__(self):
    read_only_nu = self.raw_nu.copy()
    read_only_nu.flags.writeable = False
    object.__setattr__(self, "raw_nu", read_only_nu)

  def get_clock_phases(self) -> np.ndarray:
    return np.arctan2(self.raw_nu[:, 8], self.raw_nu[:, 7])

  def get_margin_fields(self) -> np.ndarray:
    return self.raw_nu[:, 6].copy()


@dataclass(frozen=True)
class EnergyState:
  kinetic_energy: float
  potential_energy: float
  delta_energy: float

  @property
  def total_energy(self) -> float:
    return self.kinetic_energy + self.potential_energy


@dataclass(frozen=True)
class TelemetryMetrics:
  unit_change_rate: float
  delta_pos_mean: float
  delta_pos_max: float
  delta_margin_mean: float
  delta_clock_mean: float


class ParticleLanguagePayload:
  def __init__(
      self,
      timestamp_step: int,
      interval_margin: int,
      snapshot: PhysicsSnapshot,
      energy: EnergyState,
      telemetry: TelemetryMetrics,
  ):
    self._timestamp_step = timestamp_step
    self._interval_margin = interval_margin
    self._snapshot = snapshot
    self._energy = energy
    self._telemetry = telemetry

  @property
  def timestamp_step(self) -> int:
    return self._timestamp_step

  @property
  def interval_margin(self) -> int:
    return self._interval_margin

  @property
  def snapshot(self) -> PhysicsSnapshot:
    return self._snapshot

  @property
  def energy(self) -> EnergyState:
    return self._energy

  @property
  def telemetry(self) -> TelemetryMetrics:
    return self._telemetry

  def to_dict(self, include_raw: bool = False) -> Dict[str, Any]:
    data = {
        "timestamp_step": self._timestamp_step,
        "interval_margin": self._interval_margin,
        "telemetry": {
            "unit_change_rate": self._telemetry.unit_change_rate,
            "delta_pos_mean": self._telemetry.delta_pos_mean,
            "delta_pos_max": self._telemetry.delta_pos_max,
            "delta_margin_mean": self._telemetry.delta_margin_mean,
            "delta_clock_mean": self._telemetry.delta_clock_mean,
        },
        "energy": {
            "kinetic_energy": self._energy.kinetic_energy,
            "potential_energy": self._energy.potential_energy,
            "delta_energy": self._energy.delta_energy,
            "total_energy": self._energy.total_energy,
        },
        "snapshot": {
            "center_of_mass": self._snapshot.center_of_mass,
            "mean_radius": self._snapshot.mean_radius,
            "mean_clock_phase": self._snapshot.mean_clock_phase,
            "mean_margin": self._snapshot.mean_margin,
        },
    }
    if include_raw:
      data["snapshot"]["raw_nu"] = self._snapshot.raw_nu.tolist()
    return data


# =============================================================================
# 3. 近接計算
# =============================================================================
class INeighborSearch(Protocol):
  def compute_pairwise(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]: ...


class DirectPairwiseSearch:
  def compute_pairwise(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    diff = X[:, None, :] - X[None, :, :]
    r_ij = np.linalg.norm(diff, axis=-1)
    np.fill_diagonal(r_ij, 1.0)
    return diff, r_ij


# =============================================================================
# 4. 力場計算と数値積分器
# =============================================================================
class AxiomaticForceCalculator:
  def __init__(
      self, axioms: PhysicsAxioms, neighbor_search: Optional[INeighborSearch] = None
  ):
    self.axi = axioms
    self.neighbor_search = neighbor_search or DirectPairwiseSearch()

  def compute_forces_and_derivatives(
      self, nu: np.ndarray
  ) -> Tuple[np.ndarray, np.ndarray, float]:
    X, V, M, C = nu[:, 0:3], nu[:, 3:6], nu[:, 6], nu[:, 7:9]
    d_nu_non_v = np.zeros_like(nu)

    clock_phase = np.arctan2(C[:, 1], C[:, 0])
    R_i = (
        self.axi.r0_base
        + self.axi.r_phase_amp * np.cos(clock_phase * 2.0)
        + self.axi.r_margin_coef * (M - self.axi.higgs_vev)
    )

    dists = np.linalg.norm(X, axis=1, keepdims=True) + 1e-8
    radial_dev = dists.ravel() - R_i
    f_constraint = -self.axi.mu_constraint * radial_dev[:, None] * (X / dists)

    diff, r_ij = self.neighbor_search.compute_pairwise(X)
    exp_term = np.exp(-self.axi.morse_a * (r_ij - self.axi.morse_re))
    f_morse_mag = (
        -2.0 * self.axi.morse_a * self.axi.morse_de * (1.0 - exp_term) * exp_term
    )
    np.fill_diagonal(f_morse_mag, 0.0)
    f_pair = np.sum(diff * (f_morse_mag / r_ij)[:, :, None], axis=1)

    f_accel = f_constraint + f_pair
    d_nu_non_v[:, 0:3] = V

    delta2 = M**2
    dF_higgs = self.axi.higgs_lambda * M * (delta2 - self.axi.higgs_vev**2)
    weights = np.exp(-(r_ij**2) / 2.0)
    np.fill_diagonal(weights, 0.0)
    dF_grad = self.axi.d_margin * np.sum(
        weights * (M[:, None] - M[None, :]), axis=1
    )
    d_nu_non_v[:, 6] = -self.axi.mobility_margin * (dF_higgs + dF_grad)

    r2 = C[:, 0] ** 2 + C[:, 1] ** 2
    d_nu_non_v[:, 7] = (
        self.axi.sl_alpha * (1.0 - r2) * C[:, 0] - self.axi.clock_omega * C[:, 1]
    )
    d_nu_non_v[:, 8] = (
        self.axi.sl_alpha * (1.0 - r2) * C[:, 1] + self.axi.clock_omega * C[:, 0]
    )

    e_constraint = 0.5 * self.axi.mu_constraint * np.sum(radial_dev**2)
    e_higgs = self.axi.higgs_lambda * np.sum(
        0.25 * M**4 - 0.5 * (self.axi.higgs_vev**2) * M**2
    )
    morse_val = self.axi.morse_de * ((1.0 - exp_term) ** 2 - 1.0)
    np.fill_diagonal(morse_val, 0.0)
    e_morse = 0.5 * np.sum(morse_val)

    return f_accel, d_nu_non_v, float(e_constraint + e_higgs + e_morse)


class IIntegrator(Protocol):
  def step(
      self,
      nu: np.ndarray,
      calculator: AxiomaticForceCalculator,
      num_cfg: NumericalConfig,
      rng: np.random.Generator,
  ) -> Tuple[np.ndarray, float]: ...


class FaithfulVerletIntegrator:
  """数字的忠実性・半径安定を優先した Velocity Verlet + Langevin"""

  def __init__(self, gamma_base: float = 2.5, force_clip: float = 13.5):
    self.gamma_base = gamma_base
    self.force_clip = force_clip

  def step(
      self,
      nu: np.ndarray,
      calculator: AxiomaticForceCalculator,
      num_cfg: NumericalConfig,
      rng: np.random.Generator,
  ) -> Tuple[np.ndarray, float]:
    dt = num_cfg.dt
    f_accel, d_nu_non_v, pe = calculator.compute_forces_and_derivatives(nu)

    f_safe = np.clip(f_accel, -self.force_clip, self.force_clip)
    v_half = nu[:, 3:6] + 0.5 * f_safe * dt

    nu[:, 0:3] += v_half * dt
    nu[:, 6] = np.clip(nu[:, 6] + d_nu_non_v[:, 6] * dt, 0.01, 2.0)
    nu[:, 7:9] += d_nu_non_v[:, 7:9] * dt

    # クロックの数値衛生（半径1を維持）
    rclk = np.linalg.norm(nu[:, 7:9], axis=1, keepdims=True) + 1e-12
    nu[:, 7:9] /= rclk

    f_accel_next, _, current_pe = calculator.compute_forces_and_derivatives(nu)
    f_safe_next = np.clip(f_accel_next, -self.force_clip, self.force_clip)

    gamma = np.full((nu.shape[0], 1), self.gamma_base)
    c1 = np.exp(-gamma * dt)
    c2 = np.sqrt(np.maximum(num_cfg.temp_env * (1.0 - c1**2), 0.0))
    xi = rng.normal(0.0, 1.0, size=(nu.shape[0], 3))

    nu[:, 3:6] = c1 * (v_half + 0.5 * f_safe_next * dt) + c2 * xi
    return nu, current_pe


# =============================================================================
# 5. 物理エンジン
# =============================================================================
class IWorldEngine(Protocol):
  @property
  def step_count(self) -> int: ...
  def step(self) -> float: ...
  def get_state_snapshot(self) -> np.ndarray: ...


class ParticleWorldEngine(IWorldEngine):
  def __init__(
      self,
      axioms: PhysicsAxioms,
      num_cfg: NumericalConfig,
      integrator: Optional[IIntegrator] = None,
      seed: int = 20260722,
  ):
    axioms.validate()
    self.axi = axioms
    self.num_cfg = num_cfg
    self.calculator = AxiomaticForceCalculator(axioms)
    self.integrator = integrator or FaithfulVerletIntegrator()
    self.rng = np.random.default_rng(seed)

    self.nu = np.zeros(
        (self.axi.n_particles, self.axi.dim_per_particle), dtype=np.float64
    )
    self._step_count = 0
    self._init_state()

  @property
  def step_count(self) -> int:
    return self._step_count

  def _init_state(self) -> None:
    X0 = self.rng.normal(0.0, 1.0, (self.axi.n_particles, 3))
    self.nu[:, 0:3] = (
        X0 / (np.linalg.norm(X0, axis=1, keepdims=True) + 1e-8) * self.axi.r0_base
    )
    self.nu[:, 3:6] = self.rng.normal(0.0, 0.05, (self.axi.n_particles, 3))
    self.nu[:, 6] = self.rng.uniform(
        self.axi.higgs_vev * 0.88, self.axi.higgs_vev * 1.12, self.axi.n_particles
    )
    init_angles = self.rng.uniform(0.0, 2.0 * np.pi, self.axi.n_particles)
    self.nu[:, 7:9] = np.column_stack(
        [np.cos(init_angles), np.sin(init_angles)]
    )

  def step(self) -> float:
    self._step_count += 1
    self.nu, pe = self.integrator.step(
        self.nu, self.calculator, self.num_cfg, self.rng
    )
    return pe

  def get_state_snapshot(self) -> np.ndarray:
    return self.nu.copy()


# =============================================================================
# 6. Cockpit 補助
# =============================================================================
class AdaptiveEMAIntervalPolicy:
  def __init__(self, num_cfg: NumericalConfig):
    self.num_cfg = num_cfg
    self.ema_rate: float = 0.0

  def update_and_calculate_next_interval(
      self, raw_rate: float, current_interval: int
  ) -> Tuple[float, int]:
    self.ema_rate = (
        self.num_cfg.ema_alpha * raw_rate
        + (1.0 - self.num_cfg.ema_alpha) * self.ema_rate
    )
    ratio = math.exp(-self.num_cfg.sensitivity_eta * self.ema_rate)
    next_interval = int(
        self.num_cfg.min_obs_interval
        + (self.num_cfg.max_obs_interval - self.num_cfg.min_obs_interval) * ratio
    )
    next_interval = int(
        np.clip(next_interval, self.num_cfg.min_obs_interval, self.num_cfg.max_obs_interval)
    )
    return self.ema_rate, next_interval


class PayloadBuilder:
  @staticmethod
  def build(
      step_count: int,
      interval: int,
      current_nu: np.ndarray,
      delta_nu: np.ndarray,
      current_pe: float,
      last_total_energy: Optional[float],
      ema_rate: float,
  ) -> ParticleLanguagePayload:
    delta_pos = np.linalg.norm(delta_nu[:, 0:3], axis=1)
    delta_pos_mean = float(np.mean(delta_pos))

    total_ke = float(0.5 * np.sum(current_nu[:, 3:6] ** 2))
    total_energy = total_ke + current_pe
    delta_energy = (
        0.0 if last_total_energy is None else total_energy - last_total_energy
    )

    mean_cos, mean_sin = np.mean(current_nu[:, 7]), np.mean(current_nu[:, 8])
    mean_clock_phase = float(np.arctan2(mean_sin, mean_cos))

    snapshot = PhysicsSnapshot(
        center_of_mass=np.mean(current_nu[:, 0:3], axis=0).tolist(),
        mean_radius=float(np.mean(np.linalg.norm(current_nu[:, 0:3], axis=1))),
        mean_clock_phase=mean_clock_phase,
        mean_margin=float(np.mean(current_nu[:, 6])),
        raw_nu=current_nu,
    )

    energy = EnergyState(
        kinetic_energy=total_ke,
        potential_energy=current_pe,
        delta_energy=delta_energy,
    )

    telemetry = TelemetryMetrics(
        unit_change_rate=ema_rate,
        delta_pos_mean=delta_pos_mean,
        delta_pos_max=float(np.max(delta_pos)),
        delta_margin_mean=float(np.mean(np.abs(delta_nu[:, 6]))),
        delta_clock_mean=float(np.mean(np.linalg.norm(delta_nu[:, 7:9], axis=1))),
    )

    return ParticleLanguagePayload(
        timestamp_step=step_count,
        interval_margin=interval,
        snapshot=snapshot,
        energy=energy,
        telemetry=telemetry,
    )


# =============================================================================
# 7. Hub（公理的）
# =============================================================================
class IAttachmentModule(Protocol):
  def on_plp_payload(self, payload: ParticleLanguagePayload) -> None: ...


class IPublisher(Protocol):
  def broadcast(self, payload: ParticleLanguagePayload) -> None: ...


class PLPHub(IPublisher):
  def __init__(
      self,
      axioms: Optional[PhysicsAxioms] = None,
      obs_axioms: Optional[ObservationAxioms] = None,
      verbose: bool = True,
      strict: bool = False,
  ):
    self._listeners: List[IAttachmentModule] = []
    self.axioms = axioms or PhysicsAxioms()
    self.obs_axioms = obs_axioms or ObservationAxioms()
    self.verbose = verbose
    self.strict = strict
    self._broadcast_count = 0

  def connect(self, module: IAttachmentModule) -> "PLPHub":
    if module not in self._listeners:
      self._listeners.append(module)
    return self

  def disconnect(self, module: IAttachmentModule) -> "PLPHub":
    if module in self._listeners:
      self._listeners.remove(module)
    return self

  def clear(self) -> "PLPHub":
    self._listeners.clear()
    return self

  def list_modules(self) -> Sequence[str]:
    return [type(m).__name__ for m in self._listeners]

  def _validate_payload(self, payload: ParticleLanguagePayload) -> None:
    nu = payload.snapshot.raw_nu
    if nu.shape != (self.axioms.n_particles, self.axioms.dim_per_particle):
      msg = (
          f"Payload shape mismatch: expected "
          f"({self.axioms.n_particles}, {self.axioms.dim_per_particle}), got {nu.shape}"
      )
      if self.strict:
        raise ValueError(msg)
      logger.warning(f"  [HUB-AXIOM] {msg}")

    e = payload.energy
    if abs(e.total_energy - (e.kinetic_energy + e.potential_energy)) > self.obs_axioms.energy_consistency_tol:
      msg = "Energy consistency broken (total != ke + pe)"
      if self.strict:
        raise ValueError(msg)
      logger.warning(f"  [HUB-AXIOM] {msg}")

  def broadcast(self, payload: ParticleLanguagePayload) -> None:
    self._validate_payload(payload)
    self._broadcast_count += 1
    if self.verbose:
      logger.info(
          f" Hub Broadcast @ Step {payload.timestamp_step:03d} "
          f"(#{self._broadcast_count} | modules={len(self._listeners)})"
      )
    for listener in self._listeners:
      try:
        listener.on_plp_payload(payload)
      except Exception as ex:
        logger.error(f"  [HUB] Listener {type(listener).__name__} raised: {ex}")
        if self.strict:
          raise


class PLPCockpit:
  def __init__(
      self, engine: IWorldEngine, hub: IPublisher, num_cfg: NumericalConfig
  ):
    self.engine = engine
    self.hub = hub
    self.num_cfg = num_cfg
    self.policy = AdaptiveEMAIntervalPolicy(num_cfg)
    self.last_observed_nu = self.engine.get_state_snapshot()
    self.last_total_energy: Optional[float] = None
    self.current_interval = self.num_cfg.min_obs_interval
    self.next_obs_step = self.current_interval

  def process_observation(self, current_pe: float) -> None:
    current_step = self.engine.step_count
    if current_step != self.next_obs_step:
      return

    current_nu = self.engine.get_state_snapshot()
    delta_nu = current_nu - self.last_observed_nu
    delta_pos_mean = float(np.mean(np.linalg.norm(delta_nu[:, 0:3], axis=1)))

    raw_rate = delta_pos_mean / self.current_interval
    ema_rate, next_interval = self.policy.update_and_calculate_next_interval(
        raw_rate, self.current_interval
    )

    payload = PayloadBuilder.build(
        step_count=current_step,
        interval=self.current_interval,
        current_nu=current_nu,
        delta_nu=delta_nu,
        current_pe=current_pe,
        last_total_energy=self.last_total_energy,
        ema_rate=ema_rate,
    )

    self.hub.broadcast(payload)

    self.last_observed_nu = current_nu.copy()
    self.last_total_energy = payload.energy.total_energy
    self.current_interval = next_interval
    self.next_obs_step = current_step + self.current_interval


# =============================================================================
# 8. アタッチメントモジュール
# =============================================================================
class PhaseState(Enum):
  STABLE = auto()
  PERTURBATION = auto()
  TRANSITION = auto()
  RELAXATION = auto()


class FSMPhaseAnalyzerModule(IAttachmentModule):
  def __init__(self, obs_axioms: Optional[ObservationAxioms] = None) -> None:
    self.obs = obs_axioms or ObservationAxioms()
    self.current_state = PhaseState.STABLE

  def on_plp_payload(self, payload: ParticleLanguagePayload) -> None:
    rate = payload.telemetry.unit_change_rate
    d_e = abs(payload.energy.delta_energy)
    prev = self.current_state
    ax = self.obs

    if self.current_state == PhaseState.STABLE and (
        rate > ax.rate_stable_to_pert or d_e > 0.4
    ):
      self.current_state = PhaseState.PERTURBATION
    elif self.current_state == PhaseState.PERTURBATION:
      self.current_state = (
          PhaseState.TRANSITION
          if rate > ax.rate_pert_to_trans
          else (PhaseState.RELAXATION if rate < ax.rate_to_relax else self.current_state)
      )
    elif self.current_state == PhaseState.TRANSITION and rate <= ax.rate_stable_to_pert:
      self.current_state = PhaseState.RELAXATION
    elif self.current_state == PhaseState.RELAXATION:
      self.current_state = (
          PhaseState.STABLE
          if rate < ax.rate_relax_to_stable
          else (PhaseState.PERTURBATION if rate > ax.rate_relax_to_pert else self.current_state)
      )

    logger.info(
        f"  [FSM] State: {prev.name} -> {self.current_state.name} | EMA Rate: {rate:.5f}"
    )


class SyncMetricsMonitorModule(IAttachmentModule):
  def on_plp_payload(self, payload: ParticleLanguagePayload) -> None:
    phases = payload.snapshot.get_clock_phases()
    order_param = float(np.abs(np.mean(np.exp(1j * phases))))
    logger.info(
        f"  [Sync] OrderParameter: {order_param:.3f} | PhaseStd: {np.std(phases):.3f}"
    )


class PLPAnomalyDetectorModule(IAttachmentModule):
  def __init__(self, obs_axioms: Optional[ObservationAxioms] = None):
    self.obs = obs_axioms or ObservationAxioms()
    self.threshold = self.obs.energy_anomaly_threshold

  def on_plp_payload(self, payload: ParticleLanguagePayload) -> None:
    if abs(payload.energy.delta_energy) > self.threshold:
      logger.warning(
          f"  [ANOMALY] Energy Spike: {payload.energy.delta_energy:+.4f}"
          f" (Threshold: {self.threshold})"
      )


class PLPJSONLoggerModule(IAttachmentModule):
  def on_plp_payload(self, payload: ParticleLanguagePayload) -> None:
    data_bytes = len(json.dumps(payload.to_dict(include_raw=False)))
    logger.info(f"  [JSON] Payload Serialized ({data_bytes} bytes)")


# =============================================================================
# 9. エントリーポイント
# =============================================================================
if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

  axioms = PhysicsAxioms()
  num_cfg = NumericalConfig()
  obs_axioms = ObservationAxioms()

  world_engine = ParticleWorldEngine(axioms=axioms, num_cfg=num_cfg)
  plp_hub = PLPHub(axioms=axioms, obs_axioms=obs_axioms, verbose=True, strict=False)

  plp_hub.connect(FSMPhaseAnalyzerModule(obs_axioms)) \
         .connect(SyncMetricsMonitorModule()) \
         .connect(PLPAnomalyDetectorModule(obs_axioms)) \
         .connect(PLPJSONLoggerModule())

  plp_cockpit = PLPCockpit(engine=world_engine, hub=plp_hub, num_cfg=num_cfg)

  logger.info("=" * 60)
  logger.info("  PLP Kernel v10.2 | Numerically Faithful Edition")
  logger.info("  (radius std target ≈ 0.017, energy tightly controlled)")
  logger.info(f"  Modules: {plp_hub.list_modules()}")
  logger.info("=" * 60)

  for _ in range(400):
    pe = world_engine.step()
    plp_cockpit.process_observation(pe)

  logger.info("=" * 60)
  logger.info(f"  Finished. Total broadcasts: {plp_hub._broadcast_count}")
  logger.info("=" * 60)
