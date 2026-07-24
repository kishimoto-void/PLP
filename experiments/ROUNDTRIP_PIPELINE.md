# EXPERIMENT: Capsule Round-trip & Pipeline

**優先度**: 最高 · **日時**: 2026-07-24

## 目的

1. Capsule `to_dict ↔ from_dict` の忠実性
2. Input Capsule → PGRAModule → Output Capsule の構造確認

## 成功条件

| 実験 | 条件 |
|------|------|
| 1 Round-trip | 主要フィールド一致 + hash 検証 |
| 2 process_state | 距離が target 方向 + 観測が載る |
| 3 Pipeline | clock/sequence 増加 + parent_id |

## 結果

→ [RESULTS_ROUNDTRIP_PIPELINE.md](RESULTS_ROUNDTRIP_PIPELINE.md) **ALL PASS**

実行はリポジトリルートから。詳細コードは git 履歴の旧 `EXPERIMENT_ROUNDTRIP_PIPELINE.md` にも残る。
