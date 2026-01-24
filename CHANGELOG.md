# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-24

### Added

- ESXi ホストからの VM 情報収集・表示機能
- CPU ベンチマークスコアの取得・表示（cpubenchmark.net からスクレイピング）
- UPS トポロジー表示機能
- SSE によるリアルタイムデータ更新
- Prometheus 連携による稼働時間・ストレージメトリクス取得
- サーバー詳細ページ（VM 一覧、ストレージ情報、稼働時間表示）
- Docker / Kubernetes デプロイ対応

### Performance

- API レスポンス時間の最適化
- CPU ベンチマーク API をバックグラウンド取得方式に変更
- SQLite キャッシュによるデータ取得の高速化
