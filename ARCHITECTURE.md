# PLP Architecture

**Version**: 1.2 · **Project**: 1.0.0 Stable ABI Checkpoint  
**Date**: 2026-07-24

---

## Definition

> **PLP (Particle Language Protocol)** is a protocol for transporting immutable observations through stable interfaces, independent of application domains and execution environments.

> **PLP** は、不変な観測情報（Capsule）を安定した契約（Core ABI）を通じて伝達するためのプロトコルであり、実行環境や応用分野から独立して動作する。

---

## Reading path

```text
README → ARCHITECTURE → CAPSULE → specs/ → reference code → experiments/
```

---

## Stable ABI v1.0 — Freeze Scope

### Guaranteed Stable

| 契約 | 定義 |
|------|------|
| **Capsule** | 不変な観測の輸送単位（`plp_capsule.py`） |
| **CapsuleCodec** | `decode` / `encode` |
| **CapsuleModule** | `process(capsule) -> capsule` |
| **CapsulePipeline** | Module の直列合成のみ |
| **CapsuleSource** | `produce() -> capsule` |
| **CapsuleSink** | `consume(capsule) -> None` |

実装: `codecs/base.py` + `plp_capsule.py`

### Extensible

Runtime · Modules · IO · Observers · References

### 参考配線（契約を増やさない）

FanOutDispatcher · CapsuleRuntime

---

## Core Flow

```text
Source → Pipeline(Modules) → Capsule → FanOut → Sinks
```

Pipeline = 変換のみ。Runtime = 観測・保存・配信。

---

## Directory: current vs target

### 現状（v1.0.0・移行期）

```text
plp_capsule.py, plp_kernel.py, codecs/, core/, PGRA/, modules/
specs/, experiments/, docs/research/
```

`plp_capsule.py` 等がルートにあるのは **古い配置の名残**。  
Core＝Stable ABI という考えと完全一致はしていないが、**今すぐ動かさない**（外部 import 互換）。

### 目標（次メジャーで移行）

```text
plp/
├── core/          # capsule, kernel, pipeline, contracts
├── codecs/
├── modules/pgra/
├── runtime/
├── io/
└── specs/
```

移行原則: 仕様は先に固定済み。物理移動は破壊的変更としてメジャーで行う。

---

## Document roles

| 場所 | 役割 |
|------|------|
| `specs/` | 読みやすさ優先の正式仕様 |
| `experiments/` | 実験の計画と結果 |
| git 履歴 | 研究ログ・詳細版・旧フル文書 |
| `docs/research/` | 今後の論文調メモ・設計変遷 |

---

## Non-Goals（Core）

永続化・ネットワーク・推論・学習・意味解釈・実験コードの混入。

---

## 一言

> **v1.0.0 = Stable ABI + Reference Architecture + Reference Codec + Reference Module (PGRA)。**  
> 以降は契約を動かさず、Runtime / Modules / IO を育てる。

実験は忠実に実際行って。
