# PLP 引き継ぎメモ

**日時**: 2026-07-24  
**リポジトリ**: https://github.com/kishimoto-void/PLP  
**状態**: Capsule 中心アーキテクチャ確定。Codec 仕様・リファレンス実装・実験・図面まで一通り揃った段階。

---

## 1. 設計方針（確定）

PLP は「物理エンジン」や「AIフレームワーク」ではなく、

> **Capsule を媒介にしたモジュール実行基盤（Protocol Runtime）**

### 基本単位

```
Capsule
   │
   ▼
Codec.decode()  →  DecodedState
   │
   ▼
Module Logic（純粋。Capsule を知らない）
   │
   ▼
Codec.encode()  →  Capsule
```

| 概念 | 役割 |
|------|------|
| **Capsule** | 意味を持たない物理状態の輸送規格（Universal Bus） |
| **Codec** | Capsule ⇔ 内部状態の変換のみ（ロジックを持たない） |
| **Module** | 内部状態に対する処理（`process(capsule) -> capsule`） |

外部システム（Unity / ROS / MuJoCo / Live2D / LLM）は **Capsule だけ** 読めば接続できる。

詳細図は `ARCHITECTURE.md` を参照。

---

## 2. リポジトリ構成

```
PLP/
├── plp_capsule.py                 # Capsule v1.3
├── plp_kernel.py                  # 旧数値忠実 Kernel
├── CODEC_SPEC.md                  # Codec 正式仕様（公理 D1–D8, Non-Goals, 準拠レベル）
├── ARCHITECTURE.md                # アーキテクチャ図（Mermaid + ASCII）
├── SPEC.md / CAPSULE.md
├── core/                          # 世界の定義（Particle0 / Geometry / Constraint / Clock）
│   └── __init__.py                # 公開 API 明示
├── PGRA/                          # 幾何緩和エンジン v1.1
├── codecs/
│   ├── base.py                    # CapsuleCodec / CapsuleModule Protocol
│   └── pgra_codec.py              # PGRACodec + PGRAModule（リファレンス実装）
├── modules/                       # 既存監視モジュール
├── EXPERIMENT_ROUNDTRIP_PIPELINE.md
├── EXPERIMENT_RESULTS_ROUNDTRIP_PIPELINE.md   # ALL PASS
└── HANDOVER.md
```

---

## 3. 実装状況

| レイヤ | 状態 | 備考 |
|--------|------|------|
| Capsule v1.3 | 完了 | hash 32文字、from_dict 堅牢化、verify helper |
| CODEC_SPEC.md | 完了 | 公理・Non-Goals・準拠レベル・DecodeReport 仕様 |
| ARCHITECTURE.md | 完了 | 全体図・Codec 内部・Pipeline・境界 |
| PGRACodec | リファレンス実装 | DecodedState / Level / Confidence / Decoder プラグイン骨格 |
| PGRA Module | 動作 | process / process_state |
| Core 四本柱 | 完了 | Codec 接続は未 |
| CoreCodec | 未実装 | |
| Pipeline Runtime | 未実装 | |
| Round-trip 実験 | **ALL PASS** | serialize / process_state / parent_id 連鎖 |
| Python パッケージ接続 | 整備済み | core / codecs / PGRA / modules の import 経路 |

---

## 4. 次にやるべきこと（優先順）

1. **DecodeReport / evidence の本格実装**  
   仕様（CODEC_SPEC）に揃えて、confidence を根拠付きにする

2. **CoreCodec + CoreModule**  
   同じ Codec 規約で Core を Capsule 対応にする

3. **多段 Pipeline 実験**  
   Capsule → Core → PGRA → Capsule を1本通す

4. **旧 modules の Observer 化**  
   geometry_radius_monitor / energy_partition_monitor を CapsuleBuilder Observer に寄せる

---

## 5. 設計判断メモ（重要）

- Capsule を唯一の境界（Universal Bus）とする
- Codec は意味を持たない変換層（**Non-Goals を仕様に明記済み**）
- Logic は Capsule を知らない
- 準拠レベル（Minimal / Standard / Full）で自己申告可能
- 配置戦略（円周など）は公理ではなく実装依存
- 外部システムは Capsule だけ読めば接続できる
- Semantic Delay / Observer Isolation は Capsule 層で保証する

---

## 6. 主要なドキュメント

| 文書 | 内容 |
|------|------|
| `SPEC.md` | PLP Protocol 本体 |
| `CAPSULE.md` | Capsule 設計目標 |
| `CODEC_SPEC.md` | Codec 正式仕様 |
| `ARCHITECTURE.md` | アーキテクチャ図 |
| `EXPERIMENT_RESULTS_ROUNDTRIP_PIPELINE.md` | Round-trip / Pipeline 実験結果（ALL PASS） |

---

## 7. import 例（リポジトリルート基準）

```python
from plp_capsule import PLPCapsule, CapsuleSerializer, verify_content_hash
from codecs import PGRACodec, PGRAModule, DecodedState, ReconstructionLevel
from PGRA import PGRAPhysicsEngine, PhysicalState, DistanceReference
from core import Particle0, Geometry, Constraint, Clock
```

---

## 8. 一言で現状

> **プロトコルとしての設計はほぼ固まった。**  
> Capsule + Codec Spec + Architecture 図 + PGRA リファレンス実装 + Round-trip 実験（PASS）が揃っている。  
> 次は DecodeReport の実装充実、CoreCodec、多段 Pipeline。

実験は忠実に実際行って。
