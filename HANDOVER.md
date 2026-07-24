# PLP 引き継ぎメモ

**日時**: 2026-07-24  
**リポジトリ**: https://github.com/kishimoto-void/PLP  
**状態**: Capsule 中心 + Codec 仕様確定。PGRA がリファレンス実装として動作。

---

## 1. 設計方針

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

- **Capsule** = 意味を持たない物理状態の輸送規格
- **Codec**  = Capsule ⇔ 内部状態の変換のみ（ロジックを持たない）
- **Module** = 内部状態に対する処理（`process(capsule) -> capsule`）

---

## 2. リポジトリ構成

```
PLP/
├── plp_capsule.py                 # Capsule v1.3
├── plp_kernel.py                  # 旧 Kernel（数値忠実版）
├── CODEC_SPEC.md                  # ★ Codec 正式仕様
├── SPEC.md / CAPSULE.md
├── core/                          # 世界の定義（Particle0 / Geometry / Constraint / Clock）
│   └── __init__.py
├── PGRA/                          # 幾何緩和エンジン v1.1
├── codecs/                        # Capsule ⇔ 内部状態
│   ├── base.py                    # CapsuleCodec / CapsuleModule Protocol
│   └── pgra_codec.py              # PGRACodec + PGRAModule（リファレンス）
├── modules/                       # 既存監視モジュール
├── EXPERIMENT_ROUNDTRIP_PIPELINE.md
├── EXPERIMENT_RESULTS_ROUNDTRIP_PIPELINE.md
└── HANDOVER.md
```

---

## 3. 実装状況

| レイヤ | 状態 |
|--------|------|
| Capsule v1.3 | 完了 |
| CODEC_SPEC.md | 完了（公理 D1–D8, Non-Goals, 準拠レベル） |
| PGRACodec | リファレンス実装として動作（DecodedState / Level / Confidence） |
| PGRA Module | process / process_state 動作 |
| Core 四本柱 | 完了（Codec 接続は未） |
| CoreCodec | 未実装 |
| Pipeline Runtime | 未実装 |
| Round-trip 実験 | 実行済み・ALL PASS |

---

## 4. 次にやるべきこと（優先順）

1. **DecodeReport / evidence の本格実装**（仕様に揃える）
2. **CoreCodec + CoreModule**（同じ規約で）
3. **多段 Pipeline 実験**（Core → PGRA → Capsule）
4. **旧 modules の Observer 化**

---

## 5. 設計判断メモ

- Capsule を唯一の境界（Universal Bus）とする
- Codec は意味を持たない変換層（Non-Goals を仕様に明記済み）
- Logic は Capsule を知らない
- 準拠レベル（Minimal / Standard / Full）で自己申告可能
- 外部システムは Capsule だけ読めば接続できる

---

## 6. 一言で現状

> **プロトコルとしての設計はほぼ固まった。**  
> Capsule + Codec Spec + PGRA リファレンス実装が一本通っている。  
> 次は CoreCodec と多段 Pipeline、DecodeReport の実装充実。

実験は忠実に実際行って。
