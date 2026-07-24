# PLP Codec Specification

**Version**: 1.0  
**Status**: Draft  
**Date**: 2026-07-24  
**Related**: SPEC.md, ../CAPSULE.md, ../codecs/, ../ARCHITECTURE.md

---

## 1. Abstract

PLP Codec は、Capsule と内部状態（Internal State）の相互変換を担う層である。

Codec は意味を解釈しない。

Codec は観測可能な物理量だけを、最小限の内部状態へ再構成し、または内部状態を観測可能な形へ射影する。

PGRACodec は本仕様の最初のリファレンス実装である。

---

## 2. Design Axioms (D1–D8)

| ID | Name |
|----|------|
| D1 | Semantic-Free Reconstruction |
| D2 | Snapshot Immutability |
| D3 | Geometric Priority |
| D4 | Incomplete Observation Tolerance |
| D5 | Residue as Global Scalar |
| D6 | Round-trip Fidelity |
| D7 | Confidence with Evidence |
| D8 | Reconstruction Level |

詳細な定義はリポジトリ履歴および実装 `codecs/pgra_codec.py` を参照。

---

## 3. Core Types

- **ReconstructionLevel**: EXACT / PARTIAL / MINIMAL / EMPTY
- **DecodedState**: state, confidence, level, evidence, report
- **DecodeReport**: used, missing, reconstructed, unavailable, notes

---

## 4. CapsuleCodec

```text
decode(capsule) -> DecodedState
encode(state, ...) -> capsule
```

ロジックを持たない。意味解釈をしない。

---

## 5. ObservationDecoder（プラグイン）

```text
name, requires, can_decode, decode
```

---

## 6–11

Confidence は evidence ベース。MINIMAL 配置戦略は実装依存。Non-Goals: 推論・学習・意味・Simulation・拘束求解・破壊的変更・複数 Capsule 融合。

準拠: Minimal / Standard / Full

**Status**: Draft · **Version**: 1.0
