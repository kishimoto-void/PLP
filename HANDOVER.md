# PLP 引き継ぎメモ

**日時**: 2026-07-24  
**リポジトリ**: https://github.com/kishimoto-void/PLP  
**状態**: レイヤー構造（core / runtime / modules / io）を固定。Memory は Runtime Sink と位置づけ。

---

## 1. 設計方針（確定）

PLP は「物理エンジン」ではなく、

> **Capsule を媒介にしたモジュール実行基盤（Protocol Runtime）**

### 基本単位

```
Capsule
   │
   ▼
Codec.decode()  →  DecodedState
   │
   ▼
Module Logic（純粋。Capsule を知らない）
   │
   ▼
Codec.encode()  →  Capsule
   │
   ├──► 次の Module（Pipeline）
   └──► MemorySink / Logger / …（Fan-out）
```

### レイヤー

| Layer | 役割 |
|-------|------|
| **core** | Capsule / Codec / Module / Pipeline の契約 |
| **runtime** | Memory / Replay / Scheduler / Bus |
| **modules** | PGRA などの処理系 |
| **io** | Logger / Network / 永続 Store |

### Module と Sink

- **Module**: `process(capsule) -> capsule`（産む）
- **Sink**: `consume(capsule) -> None`（消費する。変更しない）

Memory は **Sink**（Runtime）。PGRA の横並び機能ではない。

詳細: `ARCHITECTURE.md` v1.1

---

## 2. リポジトリ構成（現状 → 目標）

```
現状（移行中）:
PLP/
├── plp_capsule.py / codecs/ / core/ / PGRA/ / modules/
├── CODEC_SPEC.md / ARCHITECTURE.md / SPEC.md / CAPSULE.md
└── EXPERIMENT_*.md

目標:
plp/
├── core/          # capsule, codec, module, pipeline
├── runtime/       # memory, replay, scheduler, bus
├── modules/       # pgra, …
├── io/
├── observers/
└── specs/
```

新規コードは目標レイヤーの場所に置く。既存は段階移動。

---

## 3. 実装状況

| 項目 | 状態 |
|------|------|
| Capsule v1.3 | 完了 |
| CODEC_SPEC | 完了（D1–D8, Non-Goals, 準拠レベル） |
| ARCHITECTURE v1.1 | 完了（レイヤー + Module/Sink + Fan-out） |
| PGRACodec リファレンス | 動作 |
| Round-trip 実験 | ALL PASS |
| Memory（ローカル草案） | artifacts に MemorySink 方針で再配置予定。**リポジトリ未投入** |
| CoreCodec | 未 |
| Pipeline / Bus | 未 |
| ディレクトリ物理移動 | 未（仕様先行） |

---

## 4. 次にやるべきこと（優先順）

1. **レイヤー骨格の固定を維持**（機能追加より置き場所）
2. **CapsuleSink Protocol** を core 契約に追加
3. **MemorySink** を `runtime/memory` として仕様・実装を揃える（リポジトリ投入は推敲後）
4. **Pipeline + Fan-out** の最小実装
5. **CoreCodec**（同じ Codec 規約）
6. 既存ディレクトリの段階的移動

---

## 5. 設計判断メモ

- Capsule が唯一の共有境界
- Module と Sink を分離する
- Memory は Runtime の append-only Sink（Difference First）
- Producer と Consumer は互いに知らない（Bus が配る）
- 機能を増やす前に ARCHITECTURE の置き場所に従う

---

## 6. 主要ドキュメント

| 文書 | 内容 |
|------|------|
| `ARCHITECTURE.md` | レイヤー・Module/Sink・Fan-out |
| `CODEC_SPEC.md` | Codec 正式仕様 |
| `SPEC.md` / `CAPSULE.md` | Protocol / Capsule |
| `EXPERIMENT_RESULTS_ROUNDTRIP_PIPELINE.md` | 実験 ALL PASS |

---

## 7. 一言で現状

> **プロトコルとレイヤーの置き場所は固まった。**  
> 実装は Capsule + Codec + PGRA リファレンスが通っている。  
> Memory は Runtime Sink としてローカル草案あり（未 push）。  
> 次は Sink 契約と Pipeline/Fan-out、その後に配置移動。

実験は忠実に実際行って。
