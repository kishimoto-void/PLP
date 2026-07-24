# PLP 引き継ぎメモ

**日時**: 2026-07-24  
**リポジトリ**: https://github.com/kishimoto-void/PLP  
**状態**: **Core Stable ABI v1.0 固定**。以降は契約の上に Runtime / Modules を積む。

---

## 1. Core Stable ABI v1.0（変更しない）

```text
Capsule
CapsuleCodec     decode / encode
CapsuleModule    process(capsule) -> capsule
CapsulePipeline  直列 Module のみ
CapsuleSource    produce() -> capsule
CapsuleSink      consume(capsule) -> None
```

補助実装（契約を増やさない）:

- `FanOutDispatcher` — Sink へ配るだけ
- `CapsuleRuntime` — Source → Pipeline → FanOut の薄い配線

実装: `codecs/base.py`  
図: `ARCHITECTURE.md` v1.2

### 役割分担

| 概念 | 役割 |
|------|------|
| **Pipeline** | 変換のみ |
| **Runtime** | 観測・保存・配信（Sink Fan-out） |
| **Module** | 産む |
| **Sink** | 消費する（変更しない） |
| **Source** | 入口 |

---

## 2. レイヤー

```text
core/       Stable ABI
runtime/    Memory, Replay, Scheduler, Bus, Metrics
modules/    PGRA, Fractal, …
io/         Logger, Network, Store backend
specs/      SPEC, CODEC_SPEC, CAPSULE, ARCHITECTURE
```

---

## 3. 実装状況

| 項目 | 状態 |
|------|------|
| Capsule v1.3 | 完了 |
| CODEC_SPEC | 完了 |
| Core ABI (Source/Sink/Pipeline/FanOut) | **完了** |
| ARCHITECTURE v1.2 | 完了 |
| PGRACodec / PGRAModule | リファレンス動作 |
| Round-trip 実験 | ALL PASS |
| MemorySink（ローカル） | 草案あり・**未 push** |
| ディレクトリ物理再配置 | 未（仕様先行） |

---

## 4. 次の優先順

1. **新機能を安易に Core に足さない**（ABI 固定を守る）
2. MemorySink を runtime として推敲 → 必要ならリポジトリ投入
3. 最小 Pipeline + FanOut の結合実験
4. CoreCodec（世界定義側）
5. 段階的なディレクトリ移動

---

## 5. 設計判断

- Module と Sink を分離した
- Pipeline は Sink を知らない
- FanOut だけが Sink 一覧を持つ
- Source / Sink / Module が揃い、入口→変換→消費が全部 Protocol
- Core を Stable ABI として固定し、拡張は Runtime / Modules 側

---

## 6. import 例

```python
from codecs import (
    CapsulePipeline,
    FanOutDispatcher,
    CapsuleRuntime,
    CapsuleSink,
    CapsuleSource,
    PGRAModule,
)

pipeline = CapsulePipeline().add(pgra_module)
dispatcher = FanOutDispatcher().add(memory_sink)
runtime = CapsuleRuntime(pipeline=pipeline, dispatcher=dispatcher)
out = runtime.step(input_capsule)
```

---

## 7. 一言

> **Core 契約は v1.0 として固定した。**  
> 以降は PGRA / Memory / Logger などをその上に積むだけ。  
> 機能追加より契約の安定を優先する。

実験は忠実に実際行って。
