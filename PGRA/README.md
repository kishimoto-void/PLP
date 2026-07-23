# PGRA

**Physics-Geometric Relaxation Architecture**

PGRA (Physics-Geometric Relaxation Architecture) は、**ハードウェアに依存しない幾何学的緩和アーキテクチャ**です。

CPU・GPU・FPGA・ASIC・DSP・NPU など、実行基盤を限定せず、
「差異を幾何学的に収束させる」という共通原理のみを定義します。

PGRA は特定のアルゴリズムではなく、

> **Geometry × Constraint × Difference × Relaxation**

という 4 つの概念を最小構成として扱う**汎用計算モデル**です。

---

## Philosophy

多くのシミュレーションや最適化は、

- 力を積分する
- 誤差を最小化する
- エネルギーを減少させる

という形で実装されています。

PGRA ではこれらをより抽象化し、

> **Difference（差異）を Geometry 上で Relaxation する**

という一つの原理へ統合します。

そのため、

- 剛体
- Cloth
- FEM
- Inverse Kinematics
- SoftBody
- Constraint Solver
- Animation
- Robotics
- CAD
- Circuit Layout
- AI Optimization
- Graph Optimization

などを**共通のフレームワーク**として扱えます。

---

## Hardware Independent

PGRA は命令セットではありません。  
特定の GPU API や SIMD 命令にも依存しません。

必要なのは次の概念だけです：

- Particle
- Geometry
- Constraint
- Difference
- Relaxation

つまり、

- CPU
- GPU
- CUDA / OpenCL / Metal / Vulkan Compute
- FPGA
- ASIC
- DSP
- NPU

どこでも同じ理論で動作します。

ハードウェアごとの差は

- 並列化方法
- メモリ配置
- ベクトル演算の実装

のみであり、**PGRA の数学的構造は一切変化しません**。

この設計により、**計算モデルと実装を完全に分離**できます。

---

## Core Equation

PGRA では全てを次の閉ループとして扱います：

```
Difference
    ↓
Constraint
    ↓
Geometry
    ↓
Relaxation
    ↓
Convergence
```

- **Reference** は状態を変更しません。
- Reference は「何を目標とするか」のみを定義します。

---

## Generic Architecture

```
Reference
    │
    ▼
Difference
    │
    ▼
Constraint
    │
    ▼
Geometry
    │
    ▼
Relaxation
    │
    ▼
Updated State
```

ここに Physics / AI / Robotics / Graphics などは一切書かれません。  
PGRA は**最小公理のみ**を定義します。

---

## Design Goals

- Hardware Independent
- Geometry First
- Constraint Driven
- Deterministic
- Parallel Friendly
- Solver Agnostic
- Physics Agnostic
- Scalable
- Minimal Core

---

## Applications

PGRA は以下を統一的に扱えます：

- Physics Simulation
- Position Based Dynamics (PBD)
- Cloth / SoftBody
- FEM
- Inverse Kinematics
- Robotics
- CAD
- Procedural Animation
- Particle Systems
- Multi-Agent Systems
- Neural Relaxation
- AI Optimization
- Graph Layout
- Electronic Design Automation
- Computer Vision

---

## Why PGRA?

PGRA は「物理エンジンを作るためのライブラリ」ではありません。

**差異を幾何学的に収束させるための共通アーキテクチャ**です。

そのため、物理・AI・最適化・ロボティクス・EDA など、多様な分野で同一の数理モデルを適用できます。

計算モデルとハードウェア実装を分離し、異なる実装基盤へ展開できる設計思想を重視しています。

---

## Axiom P1（現行実装）

> 物理状態は時間発展した後、シミュレーション時間を進めることなく幾何学的基準状態への差異を緩和する。

### 現行実装のデータフロー

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

### パッケージ構成

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

### 設計ポイント（実装）

- **Reference は純粋**：`evaluate_metric(state)` は State を一切変更しない
- **副作用は Strategy / Policy に集約**
- **ConvergenceMetric** で `current_magnitude` と `difference_velocity`（減少速度）を観測
- 優先度付き Reference ソート（Stability > Distance など）
- Core（`plp.core.*`）とは現時点で独立。将来 Adapter で接続予定

### v1.1 改善点（2026-07-24）

- `RelaxationStrategy` に `position_scale` と `multi_particle_damping` を追加し、ハードコードされた 0.1 を排除
- `DistanceReference` に near-zero 距離保護（eps）を追加し、数値的に安全に
- `PGRAPhysicsEngine` からスケールパラメータを外部設定可能に
- 実験時にステップサイズを調整しやすくなった

### 最小使用例

```python
from PGRA import (
    PGRAPhysicsEngine,
    DistanceReference,
    StabilityReference,
    GeometryKind,
)

# デフォルトスケールで起動
engine = PGRAPhysicsEngine()

# またはスケールを明示的に指定（実験用）
engine = PGRAPhysicsEngine(
    position_scale=1.0,
    multi_particle_damping=0.12,  # 複数粒子補正の減衰を微調整
)

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

---

## 次のステップ（PLP 連携）

1. Core の Particle0 / Geometry / Constraint / Clock への Adapter 実装
2. ConstraintSolver の導入（現在は Reference ベースの緩和のみ）
3. RK4 等の高次 Integrator
4. Capsule への ObservationBlock 接続（GeometryRadius / Energy など）

---

実験は忠実に実際行って。
