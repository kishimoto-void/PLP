# PLP Samples

実行可能なデモと結果レポート。

| サンプル | 内容 |
|----------|------|
| [particle_simulation_demo.py](particle_simulation_demo.py) | Kernel 不変・CPU vs PGRA Module 等価性デモ |
| [PLP_PARTICLE_SIMULATION_RESULTS.md](PLP_PARTICLE_SIMULATION_RESULTS.md) | 同・実行結果（ALL PASS） |

```bash
# リポジトリルートで
python samples/particle_simulation_demo.py
```

このデモは公式 `plp_capsule` / `PGRA` パッケージとは独立した最小実装です。
「同じ Kernel・違う Module → 同じ結果」を示すためのサンプルです。
