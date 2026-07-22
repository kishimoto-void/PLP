# PLP 実験: 通常処理 vs カプセル使用・開封比較

**Date**: 2026-07-23  
**Repo**: kishimoto-void/PLP  
**Kernel**: plp_kernel.py (v10.2 Numerically Faithful)  
**Capsule**: plp_capsule.py (v1.2)  
**Protocol**: PLP/1.0  
**Seed**: 20260722

---

## 1. 実験目的

同一の粒子世界状態に対して、

1. **通常処理**: 生の観測値を直接利用
2. **カプセル使用・開封**: Observer → CapsuleBuilder → JSON Serialize → Deserialize（開封）

の二経路を比較し、

- 数値の往復精度（round-trip fidelity）
- 付加メタデータ（clock / sequence / delta / hash / schema）
- Semantic Delay（意味発生の遅延）
- 解釈安定性への寄与

を整理する。

---

## 2. 実験条件

### 物理側（共通）

| パラメータ | 値 |
|-----------|-----|
| n_particles | 14 |
| mu_constraint | 18.0 |
| morse_de | 0.085 |
| r0_base | 1.70 |
| dt | 0.0155 |
| temp_env | 0.0065 |
| gamma_base | 2.5 |
| force_clip | 13.5 |
| steps | 200〜800（先行数値実験） |

### 観測内容（共通）

- Geometry: mean_radius, std_radius, com_norm
- Energy: ke, pe, total

### カプセル経路

```
Particle World
  → GeometryObserver / EnergyObserver
  → CapsuleBuilder.build(...)
  → CapsuleSerializer.to_json(...)
  → CapsuleSerializer.from_dict(...)  # 開封
  → 復元値と通常観測値を比較
```

---

## 3. 先行数値実験（Kernel v10.2）

半径・エネルギー安定性（capsule以前の基盤）:

| 指標 | 値 |
|------|-----|
| mean_r | ≈ 1.689 |
| std_r | ≈ 0.016〜0.018 |
| KE mean / std | ≈ 0.50 / 0.10 |
| Tot mean / std | ≈ -2.65 / 0.16〜0.32 |
| \|ΔE\| mean / max（観測間隔内） | ≈ 0.09 / 0.24 |

→ 数字的に安定した世界状態を、通常経路でもカプセル経路でも同じ種として扱える前提が成立。

---

## 4. 比較結果

### 4.1 処理フロー

#### 通常処理

```
Particle World
  → 直接 mean_r / std_r / KE / PE を取得
  → 変数・辞書として利用
```

特徴:
- 軽い
- 形式が自由
- clock / sequence / delta / hash / schema なし
- 受信側がすぐ意味付けしやすい（＝揺らぎやすい）

#### カプセル使用・開封

```
Particle World
  → Observer（Geometry / Energy）
  → CapsuleBuilder
  → PLPCapsule
  → JSON serialize
  → from_dict（開封）
  → ObservationBlock 群として復元
```

特徴:
- メタデータ付きで構造化
- round-trip 後も schema / capability / clock / delta / hash が残る
- 開封時点でも意味は付与されない（Semantic Delay）

---

### 4.2 数値往復精度（Round-trip）

設計上・実装上の保証:

| 項目 | 通常処理 | カプセル使用・開封後 |
|------|----------|---------------------|
| mean_radius | 生値 | 同一値が values に保持 |
| std_radius | 生値 | 同一 |
| ke / pe | 生値 | 同一 |
| 再現性（同一 seed） | 高い | 高い（観測値は決定論的に同一） |

**結論**: Capsule の serialize → open で観測値自体は失われない。  
（float の JSON 往復は通常の IEEE 表現範囲で十分一致）

---

### 4.3 情報の付加価値

| 付加情報 | 通常処理 | カプセル開封後 |
|----------|----------|----------------|
| capsule_id | なし | あり（UUID） |
| parent_id | なし | 任意で保持可 |
| schema / capability | なし | あり |
| clock / sequence | 手動 | 標準フィールド |
| delta | 手動計算 | 自動 |
| content_hash | なし | あり |
| flags | なし | compressed/encrypted/partial/realtime |

**結論**: カプセル経路はメタデータを体系的に付与する。観測値は保ったまま、共有・検証・時系列追跡が容易になる。

---

### 4.4 Semantic Delay（意味発生タイミング）

| 段階 | 通常処理 | カプセル使用・開封 |
|------|----------|-------------------|
| 観測直後 | 利用側がすぐ「これは半径」「これはエネルギー」と意味付け可能 | ObservationBlock の集合。まだ意味なし |
| 開封後 | （該当なし） | 依然として数値ブロック。意味は LLM 側 |
| LLM 受信時 | 生テキスト/生数値から自由解釈 | 統一スキーマの物理状態から解釈 |

**結論**: カプセル経路は意味生成を LLM 受信時まで遅延させる。

---

### 4.5 状態遷移抑制（概念比較）

**通常入力（言語直接）**

- 多義語・文脈依存で候補状態が分岐
- 温度パラメータにより実行ごとに解釈が揺れる

**カプセル経由**

- 同一 seed・同一世界状態 → 同一観測値
- Capsule 開封後も同一構造
- LLM への基準点が固定されるため、解釈の出発点が安定

**結論**: カプセルは「解釈そのものを固定」するのではなく、**解釈の入力基準を固定**する。結果として不要な状態探索・相転移を減らせる。

---

### 4.6 サイズ・オーバーヘッド（概算）

| 経路 | おおよそのサイズ感 |
|------|-------------------|
| 通常処理（主要スカラー数個） | 小さい（数十〜百 bytes 相当の生値） |
| Capsule JSON（Geometry + Energy + Header + Delta + Integrity） | 約 0.6〜1.0 KB 前後（メタデータ込み） |

オーバーヘッドはあるが、時系列共有・検証・多LLM配信の価値と引き換え。

---

### 4.7 簡易比較表

| 観点 | 通常処理 | カプセル使用・開封 |
|------|----------|-------------------|
| 数値の保持 | ○ | ○（round-tripで保持） |
| 形式の統一 | △（自由） | ◎（schema / capability） |
| 時間一貫性 | △ | ◎（clock / sequence / delta） |
| 検証可能性 | × | ◎（content_hash） |
| 意味の発生 | 早い | 遅い（Semantic Delay） |
| 解釈安定性 | 低め | 高め（基準点固定） |
| 実装複雑性 | 低い | 中程度 |
| 多実装・多LLM共有 | 困難 | 容易 |

---

## 実験結論

1. **数値忠実性**: カプセル化→開封で観測値は失われない。
2. **付加価値**: id / schema / capability / delta / hash / flags が乗る。
3. **Semantic Delay**: 開封時点でも意味は付与されない。意味は LLM 受信後。
4. **相転移抑制**: 言語直接入力より、共通物理状態を基準にできる分、解釈ジャンプを減らせる設計になっている。
5. **使い分け**:
   - デバッグ・瞬間的な数値確認 → 通常処理
   - LLM連携・再現実験・多実装共有 → カプセル使用

---

## 参考

- Kernel: `plp_kernel.py` (v10.2)
- Capsule: `plp_capsule.py` (v1.2)
- Design: `CAPSULE.md`
- Modules: `modules/geometry_radius_monitor.py`, `modules/energy_partition_monitor.py`

**Protocol**: PLP/1.0  
**Capsule**: v1.2  
**Date**: 2026-07-23
