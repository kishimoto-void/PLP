# PLP 引き継ぎメモ

**日時**: 2026-07-24  
**Version**: **1.0.0**（Stable ABI Checkpoint）  
**リポジトリ**: https://github.com/kishimoto-void/PLP

---

## 状態

設計段階を終え、**育てられるプロジェクト**として区切った。

- Stable ABI v1.0 凍結
- 導線: README → ARCHITECTURE → CAPSULE → specs → code → experiments
- 物理パッケージ再配置は次メジャー（互換のため）

---

## Guaranteed Stable

Capsule · Codec · Module · Pipeline · Source · Sink  
→ `plp_capsule.py` + `codecs/base.py`

## Reference

- PGRA Module + PGRACodec
- Round-trip 実験 ALL PASS（`experiments/`）

## 未着手 / 草案

- MemorySink（ローカル草案・未 push）
- CoreCodec
- ディレクトリの `plp/core/` 化

---

## 次の方針

1. Core を動かさない
2. Runtime / Modules / IO を契約の上に積む
3. 詳細研究メモは `docs/research/` または git 履歴
4. 破壊的なパス変更はメジャーバージョンで

---

## 一言

> **v1.0.0 で区切った。PGRA は PLP 上の一つの Module。**  
> 憲法は README / ARCHITECTURE / specs。実装は契約に従う。

実験は忠実に実際行って。
