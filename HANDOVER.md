# PLP 引き継ぎメモ

**日時**: 2026-07-24  
**リポジトリ**: https://github.com/kishimoto-void/PLP  
**状態**: Core 四本柱 + **PGRA v1.0 (Physics / Geometric Relaxation)** 到達。商用利用禁止ライセンス付き。

---

## 1. 何を作っているか

**Particle Language Protocol (PLP)**  
意味を持たない物理状態を運び、解釈は受信側（LLM 等）まで遅延させる通信規格＋ランタイム。

中核原則:
- Semantic Delay（意味の遅延）
- Observer Isolation（観測のみ）
- Language / LLM 非依存
- Core はデータ構造と不変条件に限定（計算・意味付けは上位層）

---

## 2. リポジトリ構成（現状）

```
PLP/
├── README.md                          # 設計思想
├── CAPSULE.md                         # Capsule 設計目標
├── SPEC.md                            # PLP Specification v1.0（RFC 寄り）
├── HANDOVER.md                        # 本ドキュメント
├── LICENSE                            # 非商用・非軍事
├── EXPERIMENT_NORMAL_VS_CAPSULE.md    # 通常処理 vs Capsule 比較
├── EXPERIMENT_CAPSULE_COMPARISON.md
├── plp_kernel.py                      # Kernel v10.2（数値忠実版）
├── plp_capsule.py                     # Capsule v1.2
├── modules/
│   ├── geometry_radius_monitor.py
│   └── energy_partition_monitor.py
├── core/                              # Core 規格実装
│   ├── particle0.py                   # 存在  v1.2
│   ├── geometry.py                    # 空間  v1.1
│   ├── constraint.py                  # 制約  v1.1
│   └── clock.py                       # 時間  v1.0
└── PGRA/                              # ★ NEW: Geometric Relaxation Architecture v1.0
    ├── __init__.py
    ├── state.py
    ├── reference.py
    ├── policy.py
    ├── strategy.py
    ├── convergence.py
    ├── integrator.py
    ├── engine.py
    └── README.md
```

---

## 3. Core（完了）

| モジュール | 役割 | schema |
|-----------|------|--------|
| Particle0 | 存在 | `plp.core.particle0/1.2` |
| Geometry | 空間 | `plp.core.geometry/1.1` |
| Constraint | 制約 | `plp.core.constraint/1.1` |
| Clock | 時間 | `plp.core.clock/1.0` |

共通 IF（全 Core モジュール）:
- `schema` / `version`
- `check_invariants()` / `is_valid()`
- `copy()` / `to_dict()` / `from_dict()`

設計上の禁止事項:
- Core に AI / Emotion / Memory / Solver を入れない
- Constraint は定義のみ（Solver は Physics Engine）
- Geometry の axes は正規直交を保証
- Particle0 は次元非依存、Frozen / Mutable 両対応

---

## 4. PGRA v1.0（NEW・Physics Module）

**PLP Geometric Relaxation Architecture**

- Reference を純粋な評価関数に分離（副作用ゼロ）
- ConvergenceMetric で **Difference + Difference Velocity** を観測
- 閉ループ幾何緩和（Axiom P1）
- 優先度付き Reference ソート
- 現時点は独立実装。将来 Core Adapter で接続予定

主要クラス:
- `PGRAPhysicsEngine`
- `DistanceReference` / `StabilityReference`
- `ConvergenceEngine`
- `MassWeightedPolicy` + `RelaxationStrategy`
- `EulerIntegrator`

詳細は `PGRA/README.md` を参照。

---

## 5. Capsule / Kernel（既存）

**Capsule v1.2** (`plp_capsule.py`)
- Header / ObservationBlock / Delta / Integrity
- Capability Enum + Registry
- Builder + Serializer + Transport Protocol
- Semantic-free を維持

**Kernel v10.2** (`plp_kernel.py`)
- 数値忠実パラメータ確定済み
- 半径 `std_r ≈ 0.017` 前後まで詰めた実績
- Hub + Attachment モジュール構成

**監視モジュール**
- GeometryRadiusMonitor
- EnergyPartitionMonitor  
（dataclass + deque + statistics API 済み）

---

## 6. 仕様・実験・ライセンス

- **SPEC.md**: MUST/SHALL ベースのプロトコル仕様草案
- **CAPSULE.md**: Capsule 設計目標（Interpretation Stability 等）
- **EXPERIMENT_***: 通常入力 vs Capsule の比較整理
- **LICENSE**: 商用利用禁止・軍事利用禁止

---

## 7. 次にやるべきこと（優先順）

1. **PGRA ↔ Core Adapter**  
   PGRA の PhysicalState / Particle を Core の Particle0 / Geometry / Constraint / Clock に接続

2. **ConstraintSolver の導入**  
   現在の Reference ベース緩和を、Core Constraint 定義に基づく Solver へ拡張

3. **Core と旧 Kernel の接続**  
   現行 `plp_kernel.py` を Core 型に寄せるか、Adapter を置く

4. **Capsule ↔ Core / PGRA の Observation 接続**  
   GeometryObserver / EnergyObserver を Core / PGRA 由来に再実装

5. **SPEC の追記**  
   Core 四モジュール + PGRA schema を SPEC.md に正式記載

6. **`core/__init__.py`**  
   公開 API をまとめる

---

## 8. 設計判断のメモ

- Core を肥大化させない（Relation / Emotion は modules 側）
- metadata 名前空間: `plp.*` / `vendor.*` / `experimental.*`
- ConstraintState: ACTIVE / DISABLED / BROKEN
- Clock は非破壊 `step()`、paused 時は進まない
- すべて「記述」と「不変条件」に寄せ、計算は上位へ
- PGRA は「時間発展 → 静的幾何緩和」の責務分離を徹底

---

## 9. 一言で現状

> **PLP Core v1 の四本柱（存在・空間・制約・時間）は揃った。**  
> **PGRA v1.0（閉ループ幾何緩和）も追加済み。**  
> 次は Core Adapter と ConstraintSolver、旧 Kernel / Capsule との接合。
