# 実験: 通常処理 vs Capsule

**Date**: 2026-07-23

同一粒子世界で「生観測」と「Capsule 化→開封」を比較。

結論:
1. 数値は round-trip で失われない
2. Capsule は id/schema/clock/delta/hash を付与
3. Semantic Delay を保てる
4. 解釈の入力基準を固定し、不要な状態分岐を減らせる

詳細比較表は git 履歴の旧ルート版を参照。
