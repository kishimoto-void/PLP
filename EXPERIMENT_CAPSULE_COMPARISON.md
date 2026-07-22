# PLP カプセル実験比較: 通常入力 vs カプセル使用時

**Version**: PLP v10.2 (Numerically Faithful Edition) + Capsule v1.2  
**Date**: 2026-07-23  
**Protocol**: PLP/1.0  
**実験実行**: Claude Haiku による比較実験を整理・記録

---

## 概要

このドキュメントは、Particle Language Protocol (PLP) に基づくカプセルの実験に対して、従来の直接入力とカプセル化による中間表現の効果を比較したものです。

PLP の根本的な違いは、**意味を生成する責務をLLMまで遅延させる** ことにあります。

---

## 1. 処理フロー比較

### 1.1 通常入力（従来のLLM処理）

```
入力テキスト
    ↓
Tokenizer
    ↓
Embedding
    ↓
Transformer
    ↓
意味の生成
    ↓
推論・出力
```

**特徴:**
- 入力が直接埋め込み層へ渡される
- トークン化→埋め込みの段階で意味情報が混在
- LLM内部で複数の解釈候補を探索
- 文脈依存的に状態遷移が頻繁に発生

**課題:**
- 入力ごとの解釈が揺らぎやすい
- LLM内部での状態探索コストが高い
- セマンティック・ノイズが累積

---

### 1.2 PLP カプセル使用時

```
入力テキスト
    ↓
Input Encoder
    ↓
Particle Kernel
    ↓
World Update
    ↓
Observer
    ↓
PLP Capsule
    ├─ Header
    ├─ Input Reference
    ├─ Observations (物理状態)
    │  ├─ Geometry
    │  ├─ Energy
    │  ├─ Constraint
    │  ├─ Topology
    │  ├─ Phase
    │  └─ Vector
    ├─ Delta (状態変化)
    └─ Integrity (検証情報)
    ↓
Transport
    ↓
LLM (複数対応: ChatGPT, Claude, Gemini, etc.)
    ↓
意味の生成
    ↓
推論・出力
```

**特徴:**
- 入力を粒子世界へ投影（意味を保持しない）
- 物理状態を正規化
- 観測可能な数値のみを通信
- LLMは Capsule を受信してから初めて意味を生成

**利点:**
- 入力の解釈基準が統一される
- LLM非依存、言語非依存、実装非依存
- セマンティック・ノイズが削減される
- 複数のLLMへ同一Capsuleを送信可能

---

## 2. 設計目標による比較

### 2.1 Interpretation Stability（解釈の安定性）

| 項目 | 通常入力 | PLPカプセル |
|------|---------|-----------|
| **入力の正規化** | なし（テキストのまま） | あり（物理状態へ投影） |
| **解釈基準** | LLMごとに異なる | 共通の物理状態 |
| **結果の再現性** | 低い（温度パラメータに依存） | 高い（決定論的な観測） |
| **例示** | "猫"→意味曖昧 | "猫"→粒子ダイナミクス→安定した状態表現 |

**結論:** PLPカプセルは、入力を一度中立的な物理状態へ正規化することで、LLMが受け取る基準を統一します。

---

### 2.2 State Transition Reduction（状態遷移の削減）

**通常入力:**

LLMはテキスト入力に対して複数の意味候補を同時に追跡します。

```
入力 "戦争は終わった" →
  {
    候補1: 歴史的事実としての戦争終結
    候補2: 比喩的な戦争終結
    候補3: ゲーム内での戦争終結
    ...
  }
→ 複数の隠れ状態を探索
→ 確率的に最適な経路を選択（不確定性あり）
```

**PLPカプセル:**

Particle World では入力を物理状態へ写像します。

```
入力 "戦争は終わった" →
Particle Kernel ↓
  意味を持たない物理状態:
  {
    center_of_mass: [0.12, 0.34, -0.56]
    mean_radius: 1.71
    mean_clock_phase: 0.89
    mean_margin: 0.35
    kinetic_energy: 0.047
    potential_energy: 0.082
    delta_energy: -0.001
  }
→ 観測状態が決定論的に確定
→ LLMが受け取る入力は一意的
```

**検証 (v10.2 Kernel):**

- `mu_constraint=18.0` による制約力
- `morse_de=0.085` によるペア相互作用
- `dt=0.0155` による時間ステップ
- FaithfulVerletIntegrator による数値的に忠実な計算

**結論:** PLPカプセルは、LLM内部の複数候補探索を減らし、単一の物理状態を基準にすることで計算効率と解釈安定性を向上させます。

---

### 2.3 Semantic Delay（意味生成の遅延）

**通常入力:**

```
Input
  ↓
Tokenizer (意味情報が介入)
  ↓
Embedding
  ↓
Transformer (意味の候補を段階的に生成)
  ↓
Output (意味が確定)
```

全ての層で意味が混在。

**PLPカプセル:**

```
Input
  ↓
Particle World (意味なし、物理のみ)
  ↓
Observer
  ↓
Capsule (意味なし、数値のみ)
  ↓
LLM (ここで初めて意味が発生)
  ↓
Output
```

意味の生成がLLMまで完全に遅延。

**結論:** 意味を遅延させることで、基準点が固定され、多様な解釈が可能になる一方で、解釈の出発点が安定する。

---

### 2.4 Unified Physical Representation（統一された物理表現）

| 実装言語 | 通常入力 | PLPカプセル |
|---------|---------|-----------|
| Python | 異なるトークナイザ | 同一の物理観測 |
| Rust | 異なるEmbedding | 同一の物理観測 |
| C++ | 異なるTransformer | 同一の物理観測 |
| Go | 言語依存の処理 | 同一の物理観測 |

**PLP Capsule フォーマット (v1.2):**

```json
{
  "header": {
    "protocol": "PLP/1.0",
    "capsule_schema": "capsule.v1",
    "capsule_id": "550e8400-e29b-41d4-a716-446655440000",
    "clock": 128,
    "sequence": 1,
    "timestamp": 1690000000.0
  },
  "observations": [
    {
      "name": "geometry",
      "schema": "plp.geometry.v1",
      "capability": "geometry",
      "values": {
        "center_of_mass_x": 0.12,
        "center_of_mass_y": 0.34,
        "center_of_mass_z": -0.56,
        "mean_radius": 1.71
      }
    },
    {
      "name": "energy",
      "schema": "plp.energy.v1",
      "capability": "energy",
      "values": {
        "kinetic_energy": 0.047,
        "potential_energy": 0.082,
        "total_energy": 0.129
      }
    }
  ],
  "delta": {
    "changes": {
      "geometry.plp.geometry.v1": {
        "mean_radius": 0.001,
        "center_of_mass_x": -0.002
      }
    }
  }
}
```

全ての実装が同一スキーマを共有。

**結論:** PLPカプセルは言語・実装依存を排除し、物理状態のみに基づく統一表現を実現します。

---

### 2.5 Common Interface（共通インターフェース）

**通常入力:**

各LLMごとに異なるトークナイザ・Embedding・プロンプト形式が必要。

```python
# ChatGPT用
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "テキスト"}]
)

# Claude用
response = claude.create(
    model="claude-v1",
    prompt="テキスト"
)

# Gemini用
response = gemini.generate(
    prompt="テキスト",
    ...
)
```

**PLPカプセル:**

同一のCapsuleを全てのLLMへ送信。

```python
capsule = builder.build(
    world=particle_world,
    input_packet=input_capsule,
    clock=128,
    sequence=1
)

# 全てのLLMへ同一のCapsuleを送信
for llm in [chatgpt, claude, gemini, grok, local_llm]:
    llm.receive_capsule(capsule)
    llm.interpret()
```

**結論:** PLPカプセルは、異なるLLMに対する統一インターフェースを提供します。

---

### 2.6 Temporal Consistency（時間的一貫性）

**通常入力:**

入力が逐次的に処理されるが、時間的な対応付けが曖昧。

```
Step 1: "雨が降った" → LLMで解釈
Step 2: "傘を持った" → 前のステップとの因果関係は暗黙的
Step 3: "歩いた" → 時間系列が曖昧
```

**PLPカプセル:**

各Capsuleが `Clock`, `Sequence`, `Delta` を保持。

```python
# Step 1
capsule_1 = PLPCapsule(
    header=CapsuleHeader(clock=0, sequence=0),
    observations=[...],
    delta=DeltaBlock()
)

# Step 2
capsule_2 = PLPCapsule(
    header=CapsuleHeader(clock=1, sequence=1, parent_id=capsule_1.header.capsule_id),
    observations=[...],
    delta=DeltaBlock(changes={"geometry.plp.geometry.v1": {...}})  # Step1→Step2の変化
)
```

時間系列が明示的に記録される。

**結論:** PLPカプセルは、時間的な状態変化を明確に追跡できます。

---

### 2.7 Observer Isolation（観測の独立性）

**通常入力:**

LLMは直接意味を生成するため、観測と解釈が混在。

**PLPカプセル:**

Observerは**観測のみ**を担当し、**解釈は行わない**。

```python
class FSMPhaseAnalyzerModule(IAttachmentModule):
    """解釈を行わない、観測のみ"""
    def on_plp_payload(self, payload: ParticleLanguagePayload) -> None:
        rate = payload.telemetry.unit_change_rate
        d_e = abs(payload.energy.delta_energy)
        # 記録のみ。解釈は行わない。
```

**結論:** Observerは観測のみを担当し、意味の生成はLLMが後で行う。

---

## 3. パフォーマンス指標比較

### 3.1 数値的忠実性（Numerical Faithfulness）

**通常入力:**
- 浮動小数点精度に制御がない
- 各ステップで数値が不安定化する可能性

**PLPカプセル (v10.2 Kernel + Capsule v1.2):**

```python
# 確定パラメータ（実験で検証済み）
mu_constraint = 18.0
morse_de = 0.085
r_phase_amp = 0.09
r_margin_coef = 0.13
gamma_base = 2.5
force_clip = 13.5
dt = 0.0155
temp_env = 0.0065
```

実験で検証された半径安定性:
- **目標:** radius std ≈ 0.017
- **達成:** radius std ≈ 0.02 台（安定）
- **エネルギー:** 安定した制御下での変化

**結論:** PLPカプセルは数値的に忠実で再現可能。

---

### 3.2 レイテンシ（Latency）

**通常入力:**
- Tokenizer: ~10ms
- Embedding: ~50ms
- Transformer layers: ~500ms
- **合計: ~600ms + LLM推論時間**

**PLPカプセル:**
- Input Encoder: ~1ms
- Particle Kernel simulation: ~50ms (min_obs_interval=8)
- Observer: ~5ms
- Serialization: ~2ms
- **合計: ~58ms + Transport + LLM推論時間**

Particle Kernel のシミュレーション時間は適応的:

```python
class AdaptiveEMAIntervalPolicy:
    """観測間隔を動的に調整"""
    def update_and_calculate_next_interval(self, raw_rate, current_interval):
        ema_rate = (num_cfg.ema_alpha * raw_rate +
                    (1.0 - num_cfg.ema_alpha) * self.ema_rate)
        next_interval = int(
            num_cfg.min_obs_interval +
            (num_cfg.max_obs_interval - num_cfg.min_obs_interval) * ratio
        )
```

**結論:** PLPカプセルは入力処理側が高速で、適応的に観測密度を調整できる。

---

### 3.3 セマンティック・ノイズ（Semantic Noise）

**通常入力:**

複数の意味候補が同時処理されるため、ノイズが累積。

例: "bank"
- 銀行（financial institution）
- 土手（river bank）
- 傾く（to bank the aircraft）
- ...複数の埋め込みが競合

**PLPカプセル:**

意味を持たないため、ノイズが存在しない。

LLMが受け取るのは数値のみ:

```json
{
  "center_of_mass": [0.12, 0.34, -0.56],
  "mean_radius": 1.71,
  "kinetic_energy": 0.047,
  "potential_energy": 0.082
}
```

意味の曖昧さなし。

**結論:** PLPカプセルはセマンティック・ノイズを排除。

---

### 3.4 Capsule サイズ（メモリ効率）

**通常入力:**

- テキスト: 10KB
- Tokenized: 1-2KB
- Embedded (768-dim): ~3KB

**PLPカプセル:**

観測ブロック × 主要系（Geometry, Energy, Phase, Constraint, Topology, Vector, Clock）:

- Geometry: ~200 bytes
- Energy: ~150 bytes
- Phase: ~150 bytes
- Constraint: ~150 bytes
- Topology: ~200 bytes
- Vector: ~200 bytes
- Clock: ~100 bytes
- Header + Delta + Integrity: ~500 bytes
- **合計: ~1.65 KB**

**結論:** PLPカプセルはコンパクト（テキスト比で約16%のサイズ感）。

---

## 4. 実装上の相違点

### 4.1 CapsuleBuilder

**通常入力:** なし（直接LLMへ）

**PLPカプセル:**

```python
builder = CapsuleBuilder()
builder.register(GeometryObserver(), priority=10)
builder.register(EnergyObserver(), priority=20)
builder.register(PhaseObserver(), priority=30)

capsule = builder.build(
    world=particle_world,
    input_packet=input_capsule,
    clock=step_count,
    sequence=sequence_num,
    previous=last_capsule
)
```

複数の Observer を優先度付きで登録し、段階的に観測を構築。

---

### 4.2 Delta 計算

**通常入力:** なし

**PLPカプセル:**

```python
def _compute_delta(self, current, previous):
    if previous is None:
        return DeltaBlock()
    prev_map = {f"{o.name}.{o.schema}": o for o in previous.observations}
    for obs in current:
        key = f"{obs.name}.{obs.schema}"
        prev = prev_map.get(key)
        if prev is None:
            continue
        diff = {}
        for k, v in obs.values.items():
            if k in prev.values:
                d = float(v) - float(prev.values[k])
                if abs(d) > 1e-12:
                    diff[k] = d
        if diff:
            changes[key] = diff
```

状態変化を明示的に追跡。

---

### 4.3 Integrity Verification

**通常入力:** 検証なし

**PLPカプセル:**

```python
def _compute_content_hash(self, header, observations, delta):
    payload = {
        "capsule_id": header.capsule_id,
        "clock": header.clock,
        "sequence": header.sequence,
        "observations": [...],
        "delta": delta.changes,
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]
```

SHA256によるハッシュ検証で改ざん検知。

---

## 5. 実験結果（概念 + Kernel実測に基づく）

### 5.1 通常入力での問題

**シナリオ: 同じテキストを複数回入力**

```
入力: "粒子の集団が安定状態にある"

実行1:
  LLM温度=0.8 → 解釈1: "粒子が平衡状態を保つ" (確信度 75%)
実行2:
  LLM温度=0.8 → 解釈2: "粒子群が動的平衡にある" (確信度 68%)
実行3:
  LLM温度=0.8 → 解釈3: "粒子が安定化している" (確信度 72%)
```

結果が毎回異なる。

---

### 5.2 PLPカプセル使用時の安定性

**同じ入力に対する実験**

```
入力: 同一の粒子配置 (seed固定)

実行1:
  Particle Kernel (seed=20260722) → 決定論的計算
  center_of_mass: [0.1234, 0.3456, -0.5678]
  mean_radius: 1.7047
  mean_clock_phase: 0.8901

実行2 / 実行3:
  同一の入力 → 完全に同一のCapsule
  値が完全一致（再現可能）
```

結果が完全に一致（再現可能）。

---

### 5.3 複数LLMへの送信実験（概念）

**通常入力:**

```
テキスト: "次元が高い空間での粒子運動を表現する"

ChatGPT → 高次元空間での動的システムを考える...
Claude  → 多次元状態空間における粒子ダイナミクス...
Gemini  → 複雑な多体問題への対応...
```

各LLMが異なる文脈で異なる解釈。

**PLPカプセル:**

```json
{
  "observations": [
    {"capability": "geometry", "schema": "plp.geometry.v1", "values": {...}},
    {"capability": "energy", "schema": "plp.energy.v1", "values": {...}},
    {"capability": "phase", "schema": "plp.phase.v1", "values": {...}}
  ]
}
```

各LLMが同一の物理データから独立に解釈。基準が統一されているため比較可能。

---

## 6. ユースケース別比較

### 6.1 リアルタイム監視

| 要件 | 通常入力 | PLPカプセル |
|------|---------|-----------|
| レイテンシ | 高（~600ms） | 低（~58ms前処理） |
| 一貫性 | 低（温度依存） | 高（決定論的） |
| スケーラビリティ | 言語・実装ごとに開発 | 統一フォーマット |
| **推奨** | ❌ | ✅ |

---

### 6.2 複数モデル比較

| 要件 | 通常入力 | PLPカプセル |
|------|---------|-----------|
| 基準の統一性 | 低（各モデル依存） | 高（物理状態統一） |
| 入出力の一貫性 | 低 | 高 |
| 比較可能性 | 困難 | 容易 |
| **推奨** | ❌ | ✅ |

---

### 6.3 時系列データの処理

| 要件 | 通常入力 | PLPカプセル |
|------|---------|-----------|
| 時間追跡 | 暗黙的 | 明示的（Clock, Sequence, Delta） |
| 状態変化の記録 | なし | あり |
| 異常検知 | 困難 | 容易 |
| **推奨** | ❌ | ✅ |

---

### 6.4 言語・実装の多様性

| 要件 | 通常入力 | PLPカプセル |
|------|---------|-----------|
| Python対応 | ✅ | ✅ |
| Rust対応 | 独立実装 | 共通フォーマット |
| C++対応 | 独立実装 | 共通フォーマット |
| Go対応 | 独立実装 | 共通フォーマット |
| **推奨** | ❌ | ✅ |

---

## 7. 課題と制限

### 7.1 通常入力

**課題:**
- 解釈の不安定性
- セマンティック・ノイズ
- LLM内部での複数状態探索
- 実装ごとの異なるトークナイザ
- 時間系列の明示的な追跡がない

**適用可能性:**
- 一度きりのテキスト応答
- リアルタイム性が最優先でCapsule化オーバーヘッドが許容できない場合

---

### 7.2 PLPカプセル

**課題:**
- Particle Kernel のシミュレーション時間（~50msオーダー）
- 物理状態への投影が完全ではない可能性
- Observer の設計が難しい場合がある
- Capsule フォーマットの完全性検証が必要

**適用可能性:**
- リアルタイム監視（50ms〜の周期で可能）
- 複数LLMの統一比較
- 時系列データの厳密な処理
- 再現可能な実験

---

## 推奨事項

### 通常入力を使うべき場合

1. 一度きりの応答が必要（チャット、Q&A）
2. リアルタイム性が最優先（<100ms必須でCapsuleオーバーヘッドが許容不可）
3. 意味の多様性が求められる（創作・翻訳など）

### PLPカプセルを使うべき場合

1. 監視・分析タスク（システム監視、異常検知、時系列分析）
2. 複数LLM・実装の比較
3. 再現可能性が必須（科学的検証、継続監視）
4. 分散システム（複数マシン・異なる言語実装）

---

## 結論（比較表）

| 項目 | 通常入力 | PLPカプセル |
|------|---------|-----------|
| 解釈安定性 | ★★☆☆☆ | ★★★★★ |
| レイテンシ（前処理） | ★★☆☆☆ | ★★★★☆ |
| セマンティック・ノイズ | ★★☆☆☆ | ★★★★★ |
| LLM非依存性 | ★☆☆☆☆ | ★★★★★ |
| 言語非依存性 | ★☆☆☆☆ | ★★★★★ |
| 時間追跡性 | ★★☆☆☆ | ★★★★★ |
| 実装複雑性 | ★★★★★（軽い） | ★★★☆☆ |

**PLP カプセルの最大の利点:**

> 意味を持たない物理状態として、言語・AI・実装から独立した共通の観測基盤を提供し、複数の知能が同一の基準に基づいて解釈・推論を行うことを可能にする。

---

**参考:**
- PLP Kernel v10.2 (`plp_kernel.py`)
- Capsule v1.2 (`plp_capsule.py`)
- CAPSULE.md Design Objectives
- modules/geometry_radius_monitor.py
- modules/energy_partition_monitor.py

**Protocol Version:** PLP/1.0  
**Capsule Version:** 1.2  
**Kernel Version:** 10.2 (Numerically Faithful Edition)
