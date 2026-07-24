# PLP Codec Specification

**Version**: 1.0  
**Status**: Draft  
**Date**: 2026-07-24  
**Related**: SPEC.md, CAPSULE.md, codecs/

---

## 1. Abstract

PLP Codec は、Capsule と内部状態（Internal State）の相互変換を担う層である。

Codec は意味を解釈しない。

Codec は観測可能な物理量だけを、最小限の内部状態へ再構成し、または内部状態を観測可能な形へ射影する。

本仕様は、すべての PLP モジュール（PGRA / Core / 将来の Fractal / Fluid / Robotics / Vision など）が共有する Codec の共通規約を定義する。

PGRACodec は本仕様の最初のリファレンス実装である。

---

## 2. Design Axioms

| ID | Name | Statement |
|----|------|-----------|
| D1 | Semantic-Free Reconstruction | Decoder は意味を復元しない。Observation → 物理状態の最小構成のみを行う。 |
| D2 | Snapshot Immutability | 復元された状態は Immutable Snapshot として扱う。破壊的変更をしない。 |
| D3 | Geometric Priority | 位置・距離・半径などの幾何情報を最優先で復元する。 |
| D4 | Incomplete Observation Tolerance | 欠落している情報は捏造しない。分からなければ空または部分状態を返す。 |
| D5 | Residue as Global Scalar | residue / stress 等は系全体の数値特徴量として扱い、意味付けは上位に委ねる。 |
| D6 | Round-trip Fidelity | encode → decode → encode したとき、観測可能な量が許容誤差内で再現されることを目指す。 |
| D7 | Confidence with Evidence | 復元結果には信頼度と、その根拠（evidence）を付与する。 |
| D8 | Reconstruction Level | 復元の忠実度を EXACT / PARTIAL / MINIMAL / EMPTY で明示する。 |

---

## 3. Core Types

### 3.1 ReconstructionLevel

```text
EXACT     明示的な粒子情報などから、観測された範囲で完全に復元できた
PARTIAL   一部の粒子または一部の次元のみ復元できた
MINIMAL   集約情報からの最小再構成（配置戦略は実装依存）
EMPTY     復元に必要な情報が不足し、空状態を返した
```

### 3.2 DecodedState

decode の標準戻り値。

```text
DecodedState
  state                 : InternalState（例: PhysicalState）
  confidence            : float          # 0.0 ～ 1.0
  level                 : ReconstructionLevel
  evidence              : list[str]      # 使用した Observation 名、欠落理由など
  report                : DecodeReport | None
```

**confidence の意味**

- 1.0 に近いほど、入力 Observation から忠実に状態を再構成できている
- 0.0 は復元不能（EMPTY）
- 固定値ではなく、使用した Observation の質と量から導出する（後述）

**is_usable（推奨ヘルパー）**

```text
confidence >= 0.5 かつ level != EMPTY
```

Module 側はこの値で「この状態をロジックに渡してよいか」を判断できる。

### 3.3 DecodeReport

研究・デバッグ・解析用の詳細報告。最低限以下の項目を持つ。

```text
DecodeReport
  used                  : list[str]      # 実際に使用した Observation 名
  missing               : list[str]      # 存在しなかったが欲しかった Observation 名
  reconstructed         : list[str]      # 復元に成功した項目（例: "position", "velocity"）
  unavailable           : list[str]      # 復元できなかった項目（例: "constraint", "reference"）
  notes                 : list[str]      # 自由記述の注意事項
```

例:

```text
used:           ["geometry.particles", "energy.kinetic"]
missing:        ["constraint.distance"]
reconstructed:  ["position", "velocity", "mass"]
unavailable:    ["constraint", "reference"]
notes:          ["velocity was zero-filled for 1 particle"]
```

---

## 4. CapsuleCodec Interface

すべての Codec が実装する最小契約。

```text
CapsuleCodec[StateT]

  decode(capsule: PLPCapsule) -> DecodedState
      Capsule の Observation から内部状態を再構成する。
      意味解釈を行わない。

  encode(
      state: StateT,
      *,
      previous: PLPCapsule | None = None,
      clock: int | None = None,
      sequence: int | None = None,
      source: str = "module",
      parent_id: str | None = None,
  ) -> PLPCapsule
      内部状態を観測し、Capsule に載せる。
```

**制約**

- Codec はロジック（緩和・積分・推論など）を持ってはならない
- Codec は Capsule の protocol / schema に従う
- encode と decode は可能な限り対称であること（D6）

---

## 5. ObservationDecoder Interface（プラグイン仕様）

特定の Observation を内部状態の一部に変換する責務を持つ。

```text
ObservationDecoder

  name: str
      担当する Observation 名（例: "geometry.particles"）

  requires: list[str] = []
      この Decoder が動作するために必要な他の Observation 名。
      空リストなら独立して動作可能。

  can_decode(obs: ObservationBlock) -> bool
      この観測を処理できるか。

  decode(obs: ObservationBlock) -> tuple[PartialState, float, DecodeReportFragment]
      PartialState : この Decoder が復元した部分状態
      float        : この観測単体の confidence 寄与
      DecodeReportFragment : 使用・欠落・復元成功/失敗の断片
```

### 5.1 依存関係の宣言

```text
class ConstraintDecoder:
    name = "constraint.distance"
    requires = ["geometry.particles"]   # Geometry が無いと動かない
```

Codec は Decoder を登録順または依存関係順に解決する。  
`requires` が満たされない Decoder はスキップされ、その旨が DecodeReport.missing に記録される。

### 5.2 登録

```text
codec.register_decoder(GeometryParticlesDecoder())
codec.register_decoder(GeometryRadiusDecoder())
codec.register_decoder(ConstraintDecoder())   # requires を持つ例
```

新しい Observation を追加しても、Codec 本体を変更せずに Decoder を追加できる。

---

## 6. Confidence 計算方針（Evidence-based）

### 6.1 原則

Confidence は固定値ではなく、**実際に使用した Observation の質と量**から導出する。

### 6.2 推奨計算（リファレンス）

```text
base = 0.0

if EXACT particle data used:
    base = 0.85 + 0.15 * (restored_particles / declared_particles)

elif only aggregate geometry used:
    base = 0.35 ～ 0.45     # 実装依存の幅を許容

elif nothing usable:
    base = 0.0

# 欠落ペナルティ
for each critical missing observation:
    base *= 0.9

confidence = clip(base, 0.0, 1.0)
```

### 6.3 Evidence

DecodedState.evidence および DecodeReport に、以下を残すことを推奨する。

- 使用した Observation 名
- 欠落した Observation 名
- 復元できた項目 / できなかった項目
- ゼロ埋めやデフォルト値を適用した項目

これにより「なぜその confidence なのか」が後から検証可能になる。

---

## 7. encode 側の責務

encode は内部状態を **意味のない数値観測** に射影する。

推奨する Observation の例：

| name | schema | 内容 |
|------|--------|------|
| geometry.radius | plp.geometry.v1 | mean / std / max radius, n_particles |
| geometry.particles | plp.geometry.particles.v1 | ids, pos, vel, mass（flat） |
| energy.kinetic | plp.energy.v1 | kinetic_energy |
| constraint.* | plp.constraint.v1 | 残差など |

粒子位置を明示的に載せる Observation（geometry.particles）を用意することで、decode 側の EXACT 復元が可能になる（D6）。

---

## 8. Module との関係

```text
Capsule
   │
   ▼
Codec.decode()  →  DecodedState
   │
   ▼
Module Logic（DecodedState.state を使用。Capsule を知らない）
   │
   ▼
Codec.encode()  →  Capsule
```

Module は Capsule を直接操作しない。  
Codec が唯一の境界である。

---

## 9. 実装上の注意

### 9.1 最小再構成の配置戦略

MINIMAL レベルで位置を再構成する場合、配置方法（円周・格子・Fibonacci 球など）は **実装依存** である。

公理ではない。  
仕様では「決定的（deterministic）であること」のみを要求し、具体的な配置は実装が選んでよい。

### 9.2 ゼロ埋めとデフォルト

速度が欠落している場合にゼロベクトルを入れる、質量が欠落している場合に 1.0 を入れる、といったデフォルト適用は許可する。  
ただしその事実は DecodeReport に記録することを推奨する。

### 9.3 捏造の禁止

存在しない粒子を「あったことにする」、存在しない拘束を生成する、といった行為は D4 に反する。

---

## 10. 準拠レベル

| レベル | 内容 |
|--------|------|
| Minimal | decode / encode を実装し、DecodedState を返す |
| Standard | ReconstructionLevel + confidence を正しく設定する |
| Full | DecodeReport と evidence を返し、ObservationDecoder をプラグイン登録できる |

リファレンス実装（PGRACodec）は Standard 以上を目指す。

---

## 11. 将来拡張（Reserved）

- Tensor / Graph / PointCloud Observation の Decoder
- 時系列 Capsule からの状態推定（ただし意味推論は禁止）
- 複数 Capsule の融合 decode
- Binary Capsule との往復

---

## 12. Related Documents

- `SPEC.md` — PLP Protocol 本体
- `CAPSULE.md` — Capsule 設計目標
- `codecs/pgra_codec.py` — 本仕様のリファレンス実装
- `HANDOVER.md` — 現状と次のステップ

---

**Status**: Draft Specification  
**Version**: 1.0  
**License**: リポジトリの LICENSE に従う

実験は忠実に実際行って。
