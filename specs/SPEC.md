# Physical Language Protocol (PLP)

**Specification Version 1.0**

---

## 1. Abstract

Physical Language Protocol (PLP) is a language-independent physical state transport protocol.

PLP does not transport semantics.

PLP transports only observable physical states.

Semantic interpretation MUST occur only after the capsule reaches the receiving system.

---

## 2. Terminology (RFC 2119)

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in RFC 2119.

---

## 3. Design Goals

### Axiom 1 — Semantic Delay
Meaning SHALL NOT exist during transport. Interpretation occurs only at the destination.

### Axiom 2 — Observer Isolation
Observers SHALL observe only. MUST NOT infer, predict, classify, or interpret.

### Axiom 3 — Physical Representation
All information SHALL be represented as physical observations (Geometry, Energy, Phase, Constraint, Vector, Clock, Topology, …).

### Axiom 4 — Language Independence
PLP MUST NOT depend upon a specific language or LLM vendor.

### Axiom 5 — Temporal Consistency
Every capsule SHALL contain Clock, Sequence, and Delta for temporal ordering.

---

## 4–18

（詳細はリポジトリ履歴の初版 SPEC と同一。Capsule / Observation / Observer / Builder / Transport / Receiver / Interpreter / Lifecycle / Errors / Versioning / Security / Compliance。）

要点:

- Capsule = Header + Input + Observation Blocks + Delta + Integrity
- Observer は観測のみ
- Interpreter の外で初めて意味が発生する

関連: `CODEC_SPEC.md`, `../ARCHITECTURE.md`, `../CAPSULE.md`, `../plp_capsule.py`

**Status**: Draft Specification · **Version**: 1.0
