# Server List

サーバーと仮想マシンの一覧を表示するWebアプリケーション。

## セットアップ

```bash
# 依存関係インストール
uv sync

# フロントエンドビルド
cd frontend && npm install && npm run build && cd ..

# CPUベンチマーク取得
uv run python -m server_list.spec.cpu_benchmark

# サーバー起動
uv run server-list
```

## アクセス

http://localhost:5000/server-list
