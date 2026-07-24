# Changelog

## [1.0.0] — 2026-07-24 — Stable ABI Checkpoint

**区切り**: 設計を作る段階 → 育てられるプロジェクト

### Guaranteed Stable

- Capsule（`plp_capsule.py`）
- CapsuleCodec / CapsuleModule / CapsulePipeline
- CapsuleSource / CapsuleSink
- 実装: `codecs/base.py`

### Reference

- Architecture: `ARCHITECTURE.md`
- Codec spec: `specs/CODEC_SPEC.md`
- Protocol: `specs/SPEC.md`
- Module: PGRA（`PGRA/`, `codecs/pgra_codec.py`）
- Experiments: `experiments/`（Round-trip ALL PASS）

### Notes

- ルートの `plp_capsule.py` / `plp_kernel.py` / `codecs/` / `core/` / `PGRA/` は **移行期の配置**
- パッケージを `plp.core.*` 等へ揃える物理移動は **次のメジャー** で行う（import 互換のため）
- 詳細な研究ログ・旧実験全文は git 履歴を参照

### Extensible (not frozen)

Runtime · Modules · IO · Observers · References · MemorySink（草案）
