# PLP Runtime — Capsule Memory

**Position**: Runtime Sink (not a Module)  
**Contract**: `consume(capsule) -> None` (CapsuleSink)

## Axioms

- M1 Immutable Memory (append-only)
- M2 Episode as Capsule Chain
- M3 Difference First
- M4 Replayability (restore only, not simulation)
- M5 Semantic Independence

## Usage

```python
from runtime.memory import MemorySink

sink = MemorySink()
sink.consume(capsule_a)
sink.consume(capsule_b)
ep = sink.close_episode(tags=["run-1"])
diffs = sink.differences(ep.episode_id)
```

Fan-out:

```text
Capsule Produced → FanOutDispatcher → MemorySink.consume
```

Demo (repo root, `PYTHONPATH=.`):

```bash
python -m runtime.memory.demo_memory
```
