Particle Language Program (PLP)

Overview

Particle Language Program (PLP) は、自然言語を直接解釈するシステムではありません。

PLPは入力を**粒子世界（Particle World）**へ投影し、その物理状態のみを観測・カプセル化して外部へ渡すための中立的なランタイムです。

PLP自身は、

- 単語の意味
- 感情
- 文脈
- 意図

を一切保持しません。

意味の解釈は受信したLLM（ChatGPT、Claude、Gemini、Grokなど）が担当します。

PLPは**「意味を持たない物理世界」**を提供します。

---

Architecture (Capsule-centric)

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

- **Capsule** = 意味を持たない物理状態の輸送規格（Universal Bus）
- **Codec**  = Capsule ⇔ 内部状態の変換のみ（ロジックを持たない）
- **Module** = 内部状態に対する処理（`process(capsule) -> capsule`）

詳細は `CODEC_SPEC.md` / `SPEC.md` / `CAPSULE.md` を参照。

---

Design Philosophy

従来のLLMでは、

Input
 ↓
Tokenizer
 ↓
Embedding
 ↓
Transformer
 ↓
Meaning

という流れになります。

PLPでは、

Input
 ↓
Particle World
 ↓
Geometry / Constraint / Vector / Phase / Energy / Topology
 ↓
Observer
 ↓
PLP Capsule
 ↓
LLM
 ↓
Meaning

となります。

つまり、

意味の生成をLLMまで遅延させる

ことがPLP最大の特徴です。

---

Core Principles

1. Semantic Free — PLPは意味を知りません
2. Observer First — 観測のみ。推論・分類をしない
3. Language Independent — 実装言語に依存しない
4. LLM Independent — 同じCapsuleをどのLLMにも送れる

---

Repository Layout

```
PLP/
├── plp_capsule.py          # Capsule v1.3
├── plp_kernel.py           # 旧数値忠実 Kernel
├── CODEC_SPEC.md           # Codec 正式仕様
├── SPEC.md / CAPSULE.md
├── core/                   # 世界の定義（Particle0 / Geometry / Constraint / Clock）
├── PGRA/                   # 幾何緩和エンジン
├── codecs/                 # Capsule ⇔ 内部状態（PGRACodec リファレンス）
├── modules/                # 監視モジュール
└── EXPERIMENT_*.md
```

---

Quick import (from repo root)

```python
from plp_capsule import PLPCapsule, CapsuleSerializer, verify_content_hash
from codecs import PGRACodec, PGRAModule, DecodedState, ReconstructionLevel
from PGRA import PGRAPhysicsEngine, PhysicalState, DistanceReference
from core import Particle0, Geometry, Constraint, Clock
```

---

Why PLP?

通常のAIは入力を直接意味へ変換します。

PLPは一度物理状態へ変換し、

意味を持たない情報

として保存・送信します。

これにより

- AI非依存
- 言語非依存
- 実装非依存

な中間表現を提供します。

PLPはAIそのものではなく、

「物理状態を運ぶための共通プロトコル兼ランタイム」

として設計されています。

---

License

Particle Language Program (PLP)

A language-independent and LLM-independent particle dynamics runtime for transmitting semantic-free physical state capsules.

The meaning is never generated inside PLP.

Meaning begins only when the receiving intelligence interprets the capsule.

実験は忠実に実際行って。
