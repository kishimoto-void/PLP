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

PLP MUST satisfy the following principles.

### Axiom 1 — Semantic Delay

Meaning SHALL NOT exist during transport.

Interpretation occurs only at the destination.

### Axiom 2 — Observer Isolation

Observers SHALL observe only.

Observers MUST NOT:

- infer
- predict
- classify
- interpret

### Axiom 3 — Physical Representation

All information SHALL be represented as physical observations.

Examples:

- Geometry
- Energy
- Phase
- Constraint
- Vector
- Clock
- Topology

### Axiom 4 — Language Independence

PLP MUST NOT depend upon:

- Python
- Rust
- C
- Java
- Go
- LLM vendor

### Axiom 5 — Temporal Consistency

Every capsule SHALL contain:

- Clock
- Sequence
- Delta

to guarantee temporal ordering.

---

## 4. Architecture

```
Input
   │
Input Encoder
   │
Particle Kernel
   │
Observers
   │
PLP Capsule
   │
Transport
   │
Receiver
   │
Interpreter
   │
LLM
```

PLP itself never performs interpretation.

---

## 5. Capsule

A Capsule SHALL consist of:

- Header
- Input (or Input Reference)
- Observation Blocks
- Delta
- Integrity

### 5.1 Header

Header fields SHOULD include:

| Field | Description |
|-------|-------------|
| protocol | e.g. `PLP/1.0` |
| capsule_schema | e.g. `capsule.v1` |
| version | Implementation version |
| capsule_id | Globally unique identifier |
| parent_id | Optional parent capsule id |
| clock | Logical or physical clock |
| sequence | Monotonic sequence number |
| timestamp | Optional wall-clock time |
| source | Origin identifier |
| flags | Transport / delivery flags |

### 5.2 Flags

Flags MAY include:

- compressed
- encrypted
- partial
- realtime

### 5.3 Input

Production implementations SHOULD prefer Input Reference over raw input
to preserve Semantic Delay.

Raw input MAY be included in development mode only.

---

## 6. Observation

ObservationBlock is the fundamental unit.

The protocol SHALL NOT define semantic meaning.

The protocol defines only structure.

Geometry, Energy, Phase, Vector, Topology, Clock, etc. are examples only.

### 6.1 ObservationBlock structure

| Field | Requirement |
|-------|-------------|
| name | REQUIRED |
| schema | REQUIRED (e.g. `plp.geometry.v1`) |
| capability | RECOMMENDED |
| values | REQUIRED (numeric map) |
| clock | OPTIONAL |

---

## 7. Capability

Capability defines:

> What kind of observation this block represents.

Capability never defines meaning.

Official capabilities SHOULD use the `plp.` namespace for schemas.

See Appendix A.

---

## 8. Observer

Observer is an isolated measurement component.

```
World
  ↓
observe()
  ↓
ObservationBlock
```

Observers SHALL NOT communicate with other observers.

Observers MUST NOT perform interpretation.

---

## 9. Builder

Builder:

- gathers observations
- computes delta
- computes integrity
- creates capsules

Builder SHALL NOT perform semantic interpretation.

---

## 10. Transport

Transport is implementation independent.

Examples:

- JSON
- Binary
- Shared Memory
- WebSocket
- TCP
- UDP
- QUIC

Transport MUST preserve capsule integrity fields.

---

## 11. Receiver

Receiver validates:

- integrity
- ordering
- schema

Receiver SHALL NOT interpret observations.

---

## 12. Interpreter

Interpretation begins only here.

```
Capsule
  ↓
Interpreter
  ↓
Meaning
```

This separation is mandatory.

---

## 13. Reference Flow

```
Human
  ↓
Sentence
  ↓
Encoder
  ↓
Particle Kernel
  ↓
Observers
  ↓
Capsule
  ↓
Network
  ↓
Receiver
  ↓
Interpreter
  ↓
LLM
  ↓
Response
```

---

## 14. Lifecycle

1. Create (Builder)
2. Serialize
3. Transport
4. Validate (Receiver)
5. Open / Deserialize
6. Interpret (outside PLP)
7. Discard or archive

Implementations SHOULD define clear ownership of capsule memory
across this lifecycle.

---

## 15. Error Conditions

Implementations SHOULD report structured errors, for example:

| Code | Meaning |
|------|---------|
| INTEGRITY_ERROR | content_hash mismatch or invalid flag |
| SCHEMA_ERROR | unknown or incompatible schema |
| CLOCK_ERROR | non-monotonic or missing clock |
| SEQUENCE_ERROR | sequence gap or reorder |
| CAPABILITY_ERROR | unknown capability where required |
| PARTIAL_ERROR | incomplete observations when partial=false |

---

## 16. Versioning Policy

- `PLP/1.x` capsules SHOULD remain backward compatible within major version 1.
- Breaking structural changes MUST increment major protocol version.
- Schema versions (e.g. `plp.geometry.v2`) MAY evolve independently
  if capability mapping remains clear.

---

## 17. Security Considerations

- content_hash provides basic integrity detection.
- Encryption and signing are OPTIONAL and belong to Transport or
  an outer security layer.
- Implementations MUST NOT treat PLP as a secure channel by itself.
- Capsules MAY be marked encrypted=true when payload is ciphertext;
  decryption is outside core PLP scope.

---

## 18. Compliance

A compliant PLP implementation MUST:

- preserve semantic delay
- isolate observers
- provide integrity verification
- maintain temporal consistency
- remain language independent

A compliance test suite MAY verify:

- round-trip of ObservationBlocks
- delta correctness against previous capsule
- hash stability for identical content
- rejection of invalid integrity

---

## 19. Future Extensions (Reserved)

- Tensor Blocks
- Graph Blocks
- Point Cloud
- Audio / Video
- Sparse Structures
- Quantum States
- Robotics
- Multi-Agent Capsules

---

## Appendix A — Recommended Capability Namespace

```
plp.geometry.v1
plp.energy.v1
plp.phase.v1
plp.vector.v1
plp.constraint.v1
plp.clock.v1
plp.topology.v1
```

External extensions SHOULD avoid the `plp.` prefix or coordinate
with the protocol maintainers.

---

## Appendix B — Related Documents

- `CAPSULE.md` — Capsule design objectives
- `plp_capsule.py` — Reference implementation (Python)
- `plp_kernel.py` — Reference Particle Kernel
- `LICENSE` — Non-commercial license

---

**Status**: Draft Specification  
**Version**: 1.0  
**License**: Non-Commercial (see LICENSE)
