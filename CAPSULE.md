# PLP Capsule Design Objectives

PLP Capsuleは、LLMの推論を制限するための仕組みではない。

目的は、入力から解釈までの間に存在する情報を、意味を持たない共通物理状態として正規化することである。

これにより、異なるLLM・異なる実装・異なるプログラミング言語でも、同一の観測情報を共有できる。

---

## Design Goals

### 1. Interpretation Stability

入力を直接LLMへ渡さず、一度Particle Worldへ投影することで、解釈の基準となる状態を統一する。

PLPは意味を生成しない。

LLMはPLP Capsuleを受け取って初めて意味を解釈する。

これにより、入力ごとの解釈の揺らぎを抑えることを目的とする。

---

### 2. State Transition Reduction

自然言語は多義性を持つ。

そのためLLM内部では複数の候補状態を探索し、解釈が何度も変化する場合がある。

PLPでは入力を一度物理状態へ写像し、

- Geometry
- Energy
- Constraint
- Phase
- Topology
- Clock
- Vector

などの数値状態へ変換する。

LLMはその状態を基準に推論するため、不必要な状態遷移を減らすことを目指す。

---

### 3. Semantic Delay

PLPは意味を持たない。

意味の生成は受信した知能（LLM）が担当する。

つまり、

```
入力
 ↓
Particle World
 ↓
Observer
 ↓
Capsule
```

までは完全に意味を持たない。

意味はCapsuleを受信した瞬間から初めて発生する。

---

### 4. Unified Physical Representation

同じ入力は、

- Python
- Rust
- C++
- C
- Go

など実装が異なっていても、

同じObserver仕様であれば同一形式のCapsuleを生成できる。

PLP Capsuleは実装依存ではなく、物理状態依存である。

---

### 5. Common Interface

PLP Capsuleは、

- ChatGPT
- Claude
- Gemini
- Grok
- Local LLM
- RL
- Unity
- Simulation

など全てのシステムへ共通の観測データを提供する。

CapsuleはAIに依存しない。

---

### 6. Temporal Consistency

ObserverはClockを持つ。

各Capsuleは

- Clock
- Sequence
- Delta

を保持することで、

世界の時間変化を一貫した形式で表現する。

---

### 7. Observer Isolation

Observerは観測のみを担当する。

解釈も推論もしない。

Observerは、

「何が起きたか」

ではなく、

「何がどれだけ変化したか」

だけを記録する。

---

## PLP Runtime

```
Human Input
 ↓
Input Encoder
 ↓
Particle Kernel
 ↓
Observer
 ↓
PLP Capsule
 ↓
Transport
 ↓
LLM
 ↓
Interpretation
```

---

## Summary

PLP Capsuleは、

意味を運ぶものではない。

PLP Capsuleは、

Particle Worldで観測された状態変化を、

言語・AI・実装から独立した共通形式として運搬するための物理状態カプセルである。

意味はPLPの中には存在しない。

意味はCapsuleを受け取った知能が初めて生成する。
