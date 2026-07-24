# PLP Architecture

**Version**: 1.2 (Stable ABI v1.0 checkpoint)  
**Date**: 2026-07-24  
**Related**: SPEC.md, CAPSULE.md, CODEC_SPEC.md, HANDOVER.md, README.md

---

## Definition

> **PLP (Particle Language Protocol)** is a protocol for transporting immutable observations through stable interfaces, independent of application domains and execution environments.

> **PLP** は、不変な観測情報（Capsule）を安定した契約（Core ABI）を通じて伝達するためのプロトコルであり、実行環境や応用分野から独立して動作する。

---

## Stable ABI v1.0 — Freeze Scope

### Guaranteed Stable（互換を維持する）

| 契約 | 定義 |
|------|------|
| **Capsule** | 不変な観測の輸送単位（`plp_capsule.py`） |
| **CapsuleCodec** | `decode` / `encode` |
| **CapsuleModule** | `process(capsule) -> capsule` |
| **CapsulePipeline** | Module の直列合成のみ |
| **CapsuleSource** | `produce() -> capsule` |
| **CapsuleSink** | `consume(capsule) -> None` |

これらは **v1.0 として凍結**する。  
メソッドの追加・削除・意味の変更は行わない。

実装: `codecs/base.py` + `plp_capsule.py`

### Extensible（自由に拡張してよい）

| 領域 | 例 |
|------|-----|
| **Runtime** | MemorySink, Replay, Scheduler, Metrics, FanOut の登録内容 |
| **Modules** | PGRA, Fractal, Physics, … |
| **IO** | Logger, Network, FileSource, SocketSource, Visualizer |
| **Observers** | geometry / energy 等の観測プラグイン |
| **References** | DistanceReference 等の幾何基準 |

### 参考配線（契約を増やさない）

| 型 | 位置づけ |
|----|----------|
| **FanOutDispatcher** | Runtime 補助。Sink 一覧を持ち配るだけ |
| **CapsuleRuntime** | Source → Pipeline → FanOut の薄いループ |

Protocol の表面積は増やさない。便利な配線に留める。

---

## Guiding Principle

> **Capsule だけを知る。互いに知らない。**

Core 契約は変更しない。  
Runtime / Modules / IO はその上に積む。

---

## Core Flow

```text
Source
  ↓
Pipeline (Modules only)     ← 変換
  ↓
Capsule
  ↓
FanOutDispatcher            ← 観測・保存・配信
  ├── MemorySink
  ├── LoggerSink
  ├── NetworkTransport
  └── …
```

| 概念 | 役割 |
|------|------|
| **Pipeline** | 変換のみ。Sink を知らない |
| **Runtime** | 観測・保存・配信（Sink Fan-out） |
| **Module** | 産む `process` |
| **Sink** | 消費する `consume`（変更しない） |
| **Source** | 入口 `produce` |

---

## Layer Model (Target)

```text
plp/
├── core/          # Stable ABI（Capsule, Codec, Module, Pipeline, Source, Sink）
├── runtime/       # Memory, Replay, Scheduler, Bus, Metrics
├── modules/       # PGRA, Fractal, Physics, …
├── io/            # Logger, Network, persistent Store, Visualizer
├── observers/
├── references/
└── specs/         # SPEC, CODEC_SPEC, CAPSULE, ARCHITECTURE
```

---

## Directory Reality Check（現状）

**ドキュメントの目標レイアウトと、物理ディレクトリはまだ一致していない。**  
仕様を先行固定し、移動は段階的に行う。

| 現在のパス | 目標上の位置 | 状態 |
|------------|--------------|------|
| `plp_capsule.py` | core/capsule | 契約本体・安定 |
| `codecs/base.py` | core contracts | **Stable ABI 実装済み** |
| `codecs/pgra_codec.py` | modules/pgra + codec | リファレンス実装 |
| `core/` (Particle0…) | world 定義 | 存在（Codec 接続は未） |
| `PGRA/` | modules/pgra | 存在 |
| `modules/` (monitors) | observers/ | 存在 |
| Memory | runtime/memory | **ローカル草案のみ・未 push** |
| `*_SPEC.md` / `ARCHITECTURE.md` | specs/ | ルートに配置（憲法） |

### Core 配下の監査

- `codecs/base.py` に実験コードは含まれない
- Protocol + Pipeline + FanOut/Runtime 配線のみ
- PGRA・Memory・実験スクリプトは Core 契約ファイルに混在していない

---

## Minimal Protocols

```python
class CapsuleModule(Protocol):
    def process(self, capsule: PLPCapsule) -> PLPCapsule: ...

class CapsuleSink(Protocol):
    def consume(self, capsule: PLPCapsule) -> None: ...

class CapsuleSource(Protocol):
    def produce(self) -> PLPCapsule: ...
```

検索・close・connect などは各実装の固有 API。Core に足さない。

---

## Non-Goals（Core）

- 永続化・ネットワーク・UI
- 推論・学習・意味解釈
- Sink 検索 API の統一
- Module 間の直接呼び出し規約
- 実験コードの混入

---

## 一言

> **Core = 変更しない契約（Stable ABI v1.0）。**  
> Pipeline は変換、Runtime は観測・保存・配信。  
> 以降は契約を動かさず、Runtime / Modules / IO を育てる。

実験は忠実に実際行って。
