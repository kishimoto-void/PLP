# PLP 引き継ぎメモ

**日時**: 2026-07-24  
**Version**: **1.0.0**（Stable ABI Checkpoint） + Runtime Memory 追加  
**リポジトリ**: https://github.com/kishimoto-void/PLP

---

## 状態

- Stable ABI v1.0 凍結
- **MemorySink を `runtime/memory/` に追加済み**（Runtime Sink）
- 導線: README → ARCHITECTURE → CAPSULE → specs → code → experiments

---

## Guaranteed Stable (Core)

Capsule · Codec · Module · Pipeline · Source · Sink  
→ `plp_capsule.py` + `codecs/base.py`

## Runtime（拡張）

| パス | 内容 |
|------|------|
| `runtime/memory/` | MemorySink · Store · Difference · Replay |

```python
from runtime.memory import MemorySink
sink = MemorySink()
sink.consume(capsule)
ep = sink.close_episode(tags=["run"])
```

Core 契約は `consume` のみ。Difference / Episode は Sink 固有 API。

## Reference Module

PGRA + PGRACodec · Round-trip experiments ALL PASS

## 未着手

- CoreCodec
- ディレクトリの `plp/core/` 化（次メジャー）
- Memory 永続バックエンド

---

実験は忠実に実際行って。
