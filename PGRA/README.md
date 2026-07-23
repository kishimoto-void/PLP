# PLP Geometric Relaxation Architecture (PGRA) v1.0

**PLP の物理層（Physics Module）**

Reference を純粋な「基準・評価データ」に引き戻して副作用（relax() による直接的な状態書き換え）を削ぎ落とすと同時に、**「差異（Difference）とその減少速度（Difference Velocity）」を収束指標（ConvergenceMetric）として観測する閉ループ幾何緩和**へとリファクタリングした標準実装例です。

## Axiom P1

> 物理状態は時間発展した後、シミュレーション時間を進めることなく幾何学的基準状態への差異を緩和する。

## データ・処理フロー

```
Application / Hardware Layer
       │  (機体固有の関節制限・支持多角形・可動域)
       ▼
Reference Generator ────> [ Pure Reference ] (評価のみ・副作用ゼロ)
                                 │
                                 ▼ evaluate_metric()
                        [ Geometric Metric ] (スカラー誤差 + 生誤差ベクトル)
                                 │
                                 ▼
                    [ Convergence Engine ] (Metric & Difference Velocity 観測)
                                 │
                                 ▼ apply_correction()
                     [ Relaxation Strategy ]
                                 │
                                 ▼
                     [ Correction Policy ] ──> PhysicalState 更新
```

## パッケージ構成

```
PGRA/
├── __init__.py
├── state.py          # Particle / Geometry / PhysicalState
├── reference.py      # Pure Reference + GeometricMetric
├── policy.py         # CorrectionPolicy (MassWeighted)
├── strategy.py       # RelaxationStrategy
├── convergence.py    # ConvergenceEngine + Difference Velocity
├── integrator.py     # EulerIntegrator (TimeIntegrator Protocol)
├── engine.py         # PGRAPhysicsEngine
└── README.md
```

## 設計ポイント

- **Reference は純粋**：`evaluate_metric(state)` は State を一切変更しない。
- **副作用は Strategy / Policy に集約**。
- **ConvergenceMetric** で `current_magnitude` と `difference_velocity`（減少速度）を観測。
- 優先度付き Reference ソート（Stability > Distance など）。
- Core（`plp.core.*`）とは現時点で独立。将来 Adapter で接続予定。

## 最小使用例

```python
from PGRA import (
    PGRAPhysicsEngine,
    DistanceReference,
    StabilityReference,
    GeometryKind,
)

engine = PGRAPhysicsEngine()

engine.add_particle("p1", [0.0, 0.0, 0.0], mass=1.0)
engine.add_particle("p2", [1.5, 0.0, 0.0], mass=1.0)
engine.add_geometry("support", GeometryKind.POLYGON, ["p1", "p2"])

engine.add_reference(
    DistanceReference("dist01", "p1", "p2", distance=1.0, priority=50)
)

# 静的緩和のみ
metrics = engine.geometric_relaxation(epsilon=1e-5, max_iterations=20)

# または時間発展 + 緩和
state = engine.step(dt=0.01)
```

## 次のステップ（PLP Handover 連携）

1. Core の Particle0 / Geometry / Constraint / Clock への Adapter 実装
2. ConstraintSolver の導入（現在は Reference ベースの緩和のみ）
3. RK4 等の高次 Integrator
4. Capsule への ObservationBlock 接続（GeometryRadius / Energy など）

---

実験は忠実に実際行って。
