# PLP 引き継ぎメモ

**日時**: 2026-07-24  
**リポジトリ**: https://github.com/kishimoto-void/PLP  
**状態**: **Stable ABI v1.0 チェックポイント**。Core 契約を凍結。以降は Runtime / Modules / IO を育てる。

---

## Definition

> PLP は、不変な観測情報（Capsule）を安定した契約（Core ABI）を通じて伝達するためのプロトコルであり、実行環境や応用分野から独立して動作する。

---

## Stable ABI v1.0

### Guaranteed Stable

- Capsule
- CapsuleCodec
- CapsuleModule
- CapsulePipeline
- CapsuleSource
- CapsuleSink

実装: `plp_capsule.py` + `codecs/base.py`

### Extensible

- Runtime / Modules / IO / Observers / References

### 参考配線（契約を増やさない）

- FanOutDispatcher
- CapsuleRuntime

---

## 監査結果（このチェックポイント）

| 項目 | 結果 |
|------|------|
| Core に実験コードが混在していないか | **OK** — `codecs/base.py` は Protocol + 薄い配線のみ |
| ARCHITECTURE と実ディレクトリ | **仕様先行** — 目標レイアウトと物理配置は未一致。移行は段階的 |
| 凍結範囲の明記 | **OK** — Guaranteed Stable / Extensible を ARCHITECTURE・README に記載 |
| 一文定義 | **OK** — README / ARCHITECTURE 先頭 |

---

## 実装状況

| 項目 | 状態 |
|------|------|
| Capsule v1.3 | 完了 |
| Core Stable ABI | **v1.0 凍結** |
| CODEC_SPEC | 完了 |
| ARCHITECTURE | 憲法として整備 |
| PGRACodec / PGRAModule | リファレンス動作 |
| Round-trip 実験 | ALL PASS |
| MemorySink | ローカル草案・**未 push** |
| ディレクトリ再配置 | 未（仕様固定後に実施） |

---

## 次の方針

1. **Core を動かさない**
2. MemorySink を runtime として推敲 → 必要なら投入
3. Pipeline + FanOut の結合実験
4. CoreCodec（世界定義）
5. 物理ディレクトリの段階移動（core/runtime/modules/io/specs）

---

## 一言

> **Stable ABI v1.0 として区切った。**  
> 憲法（README / ARCHITECTURE / CODEC_SPEC）を先に固定し、実装は契約の上に積む。  
> PGRA は PLP の上で動く一つの Module である。

実験は忠実に実際行って。
