# PLP 引き継ぎメモ

**日時**: 2026-07-24  
**リポジトリ**: https://github.com/kishimoto-void/PLP  
**状態**: Capsule 中心アーキテクチャ + Codec 分離 へ移行開始

---

## 1. 設計方針の更新（重要）

PLP は「物理エンジン」や「AIフレームワーク」ではなく、

> **Capsule を媒介にしたモジュール実行基盤（Protocol Runtime）**

として位置付ける。

### 基本単位

```
Capsule
   │
   ▼
Codec.decode()
   │
   ▼
Internal State
   │
   ▼
Module Logic（純粋）
   │
   ▼
Internal State
   │
   ▼
Codec.encode()
   │
   ▼
Capsule
```

- **Codec** = Capsule ⇔ 内部状態の相互変換のみ（ロジックを持たない）
- **Logic** = 内部状態に対する処理（Capsule を一切知らない）
- すべてのモジュールは `process(capsule) -> capsule` だけを実装する

### 利点

- Codec だけ単体で Round-trip テスト可能
- Logic は純粋なアルゴリズムとして保てる
- Capsule のバージョン変更は Codec のみに影響
- Unity / ROS / MuJoCo / Live2D などは Capsule だけ読めば接続可能

---

## 2. リポジトリ構成（現状）

```
PLP/
├── plp_capsule.py              # Capsule v1.3（通信規格）
├── plp_kernel.py               # 旧 Kernel（数値忠実版）
├── core/                       # 世界の定義（Particle0 / Geometry / Constraint / Clock）
├── PGRA/                       # 幾何緩和エンジン
├── codecs/                     # ★ NEW: Capsule ⇔ 内部状態
│   ├── __init__.py
│   ├── base.py                 # CapsuleCodec / CapsuleModule Protocol
│   └── pgra_codec.py           # PGRACodec + PGRAModule
├── modules/                    # 既存監視モジュール
├── SPEC.md
├── CAPSULE.md
├── HANDOVER.md
└── ...
```

---

## 3. 現在の実装状況

| レイヤ | 状態 |
|--------|------|
| Capsule v1.3 | 完了（hash 32文字、from_dict 堅牢化、verify helper） |
| PGRA v1.1 | 完了（スケールパラメータ化） |
| Core 四本柱 | 完了 |
| codecs/base.py | Protocol 定義済み |
| codecs/pgra_codec.py | 骨格実装済み（decode は簡易、encode は動作） |
| CoreCodec | 未実装 |
| Pipeline Runtime | 未実装 |

---

## 4. 次にやるべきこと（優先順）

1. **PGRACodec.decode の本格実装**  
   ObservationBlock から PhysicalState を正しく復元できるようにする

2. **CoreCodec + CoreModule**  
   同様の Codec + Logic 分離で Core を Capsule 対応にする

3. **Round-trip テスト**  
   Codec の encode → decode が情報を失わないことを検証

4. **簡単な Pipeline 実験**  
   Capsule → PGRAModule → Capsule の一連の流れを動かす

5. **旧 Kernel / modules の Observer 化**  
   既存の監視コードを CapsuleBuilder の Observer に寄せる

---

## 5. 設計判断メモ

- Capsule を唯一の境界（Universal Bus）とする
- Adapter ではなく **Codec** と呼ぶ（役割がより明確）
- Logic は Capsule を知らない
- 外部システムは Capsule だけを実装すれば接続できる
- Semantic Delay / Observer Isolation は Capsule 層で保証する

---

## 6. 一言で現状

> **Capsule を共通バスとし、Codec と Logic を分離するアーキテクチャへ移行を開始した。**  
> PGRA はその第一実装として Codec + Module の骨格が動く状態。  
> 次は decode の充実と Core 側の対応。

実験は忠実に実際行って。
