# Particle Language Protocol (PLP)

**Axiomatic, Pipeline-Oriented Production Kernel**  
**v10.2 — Numerically Faithful Edition**

粒子系を「言語」として扱うための公理的パイプラインカーネル。  
物理公理 → 数値積分 → 適応的観測 → 言語パケット（Payload） → Hub によるモジュール配信、という構成で、実験と本番の両方に耐える設計を目指しています。

## 現在の位置付け（v10.2）

- **数字的忠実性**を優先してパラメータを確定
- 半径揺らぎ `std_r ≈ 0.017`
- 全エネルギー揺らぎを大きく抑制（Tot std ≈ 0.16〜0.32）
- Hub が公理に照らしてペイロード整合性を検証
- 観測閾値・相転移閾値も公理層（`ObservationAxioms`）に昇格

## 主要構成

| 層 | 役割 |
|------|------|
| `PhysicsAxioms` / `NumericalConfig` / `ObservationAxioms` | 公理層（不変パラメータ） |
| `ParticleWorldEngine` + `FaithfulVerletIntegrator` | 物理時間発展 |
| `PLPCockpit` | 適応的観測オーケストレーター |
| `PLPHub` | 公理的言語バス（メインHub） |
| Attachment Modules | 下記参照 |

## Attachment Modules

### 組み込み（plp_kernel.py 内）
- `FSMPhaseAnalyzerModule` — 相状態機械
- `SyncMetricsMonitorModule` — Order Parameter / 位相標準偏差
- `PLPAnomalyDetectorModule` — エネルギー異常検知
- `PLPJSONLoggerModule` — ペイロードシリアライズ確認

### 追加モジュール（`modules/`）
- **[`geometry_radius_monitor.py`](./modules/geometry_radius_monitor.py)**  
  半径統計（mean / std / min-max / skew / kurtosis）、COMドリフト、拘束エネルギーとの相関
- **[`energy_partition_monitor.py`](./modules/energy_partition_monitor.py)**  
  KE / 拘束PE / Morse PE / Higgs PE の内訳と支配割合

## 実行

```bash
python plp_kernel.py
```

追加モジュールを使う例:

```python
from plp_kernel import *
from modules.geometry_radius_monitor import GeometryRadiusMonitorModule
from modules.energy_partition_monitor import EnergyPartitionMonitorModule

# ... engine / hub 作成後
hub.connect(GeometryRadiusMonitorModule(axioms))
   .connect(EnergyPartitionMonitorModule(axioms))
```

## 確定パラメータ（v10.2）

```text
mu_constraint      = 18.0
morse_de           = 0.085
r_phase_amp        = 0.09
r_margin_coef      = 0.13
gamma_base         = 2.5
force_clip         = 13.5
dt                 = 0.0155
temp_env           = 0.0065
```

## 設計方針

- 公理は `frozen=True` の dataclass で固定
- Payload は不変集約オブジェクト
- Hub はチェーン可能な接続と整合性検証を持つ
- 数値積分は半径安定とエネルギー制御を優先した FaithfulVerlet

---

**Main Hub file**: [`plp_kernel.py`](./plp_kernel.py)

製作者: kishimoto-void  
