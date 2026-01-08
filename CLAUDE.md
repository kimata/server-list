# CLAUDE.md

このファイルは Claude Code がこのリポジトリで作業する際のガイダンスを提供します。

## 概要

ESXi ホスト上の仮想マシン情報をリアルタイムで収集・表示するダッシュボードアプリケーションです。Flask バックエンドと React フロントエンドで構成され、pyVmomi を使用して ESXi から VM 情報を取得し、SQLite でキャッシュします。

## 重要な注意事項

### コード変更時のドキュメント更新

コードを更新した際は、以下のドキュメントも更新が必要か**必ず検討してください**:

| ドキュメント | 更新が必要なケース                                                 |
| ------------ | ------------------------------------------------------------------ |
| README.md    | 機能追加・変更、使用方法の変更、依存関係の変更、API 変更           |
| CLAUDE.md    | アーキテクチャ変更、新規モジュール追加、設定項目変更、開発手順変更 |

### my-lib（共通ライブラリ）の修正について

`my_lib` のソースコードは **`../my-py-lib`** に存在します。

リファクタリング等で `my_lib` の修正が必要な場合:

1. **必ず事前に何を変更したいか説明し、確認を取ること**
2. `../my-py-lib` で修正を行い、commit & push
3. このリポジトリの `pyproject.toml` の my-lib のコミットハッシュを更新
4. `uv lock && uv sync` で依存関係を更新

```bash
# my-lib 更新の流れ
cd ../my-py-lib
# ... 修正 ...
git add . && git commit -m "変更内容" && git push
cd ../server-list
# pyproject.toml の my-lib ハッシュを更新
uv lock && uv sync
```

### プロジェクト管理ファイルについて

以下のファイルは **`../py-project`** で一元管理しています:

- `pyproject.toml`
- `.pre-commit-config.yaml`
- `.gitignore`
- `.gitlab-ci.yml`
- その他プロジェクト共通設定

**これらのファイルを直接編集しないでください。**

修正が必要な場合:

1. **必ず事前に何を変更したいか説明し、確認を取ること**
2. `../py-project` のテンプレートを更新
3. このリポジトリに変更を反映

## 開発環境

### パッケージ管理

- **パッケージマネージャー**: uv
- **依存関係のインストール**: `uv sync`
- **依存関係の更新**: `uv lock --upgrade-package <package-name>`

### テスト実行

テストは3層構造で管理されています:

```bash
# ユニットテスト（ESXi アクセスなし、高速）
uv run pytest tests/unit/

# 統合テスト（Flask アプリ使用）
uv run pytest tests/integration/

# E2E テスト（外部サーバー + Playwright 必要）
uv run pytest tests/e2e/ --host <host> --port <port>

# 型チェック
uv run python -m pyright
uv run mypy src/

# 全テスト（E2E 除く）
uv run pytest
```

### アプリケーション実行

```bash
# サーバー起動
uv run server-list-webui -c config.yaml

# デバッグモード
uv run server-list-webui -c config.yaml -D

# ポート指定
uv run server-list-webui -c config.yaml -p 8080
```

### フロントエンド開発

```bash
# 開発サーバー起動
cd frontend && npm run dev

# 本番ビルド
cd frontend && npm run build

# 型チェック
cd frontend && npm run type-check
```

## アーキテクチャ

### ディレクトリ構成

```
src/server_list/
├── __init__.py
├── __main__.py                 # エントリーポイント（server-list コマンド）
├── cli/
│   └── webui.py                # Flask アプリ作成・起動（server-list-webui）
│
└── spec/
    ├── cache_manager.py        # config.yaml キャッシュ管理（SQLite + 定期更新）
    ├── cpu_benchmark.py        # cpubenchmark.net スクレイピング
    ├── data_collector.py       # ESXi データ収集（pyVmomi、5分間隔）
    │
    └── webapi/
        ├── config.py           # GET /api/config - 設定 + VM 情報
        ├── vm.py               # /api/vm/* - VM 情報 API
        ├── cpu.py              # /api/cpu/* - CPU ベンチマーク API
        └── uptime.py           # /api/uptime/* - 稼働時間 API

frontend/src/
├── App.tsx                     # ルーティング設定
├── main.tsx                    # エントリーポイント
├── types/
│   └── config.ts               # TypeScript 型定義
├── pages/
│   ├── HomePage.tsx            # サーバー一覧ページ
│   └── MachineDetailPage.tsx   # サーバー詳細ページ
├── components/
│   ├── ServerCard.tsx          # サーバーカードコンポーネント
│   ├── VMTable.tsx             # VM テーブル（リソース使用状況含む）
│   ├── PerformanceBar.tsx      # 性能バー表示
│   ├── StorageInfo.tsx         # ストレージ情報表示
│   ├── UptimeDisplay.tsx       # 稼働時間表示
│   └── VMList.tsx              # VM リスト
└── hooks/
    └── useEventSource.ts       # SSE 接続フック

tests/
├── conftest.py                 # 共通フィクスチャ
├── unit/                       # ユニットテスト（20+ファイル）
│   ├── test_webapi_*.py        # API エンドポイントテスト
│   ├── test_cpu_benchmark*.py  # CPU ベンチマーク関連
│   ├── test_cache_manager*.py  # キャッシュ管理関連
│   └── test_data_collector*.py # データ収集関連
├── integration/                # 統合テスト
│   └── test_api.py
└── e2e/                        # E2E テスト（Playwright）
    ├── conftest.py
    └── test_webui.py

schema/                         # JSON Schema 定義
├── config.schema               # config.yaml スキーマ
├── secret.schema               # secret.yaml スキーマ
└── sqlite.schema               # SQLite テーブル定義
```

### コアコンポーネント

#### データ収集 (`data_collector.py`)

ESXi ホストからのデータ収集を担当:

- **pyVmomi** を使用して ESXi API に接続
- VM 情報（CPU、メモリ、ストレージ、電源状態）を取得
- ホスト情報（稼働時間、CPU スレッド数）を取得
- **5分間隔**でバックグラウンドスレッドが自動更新
- 取得データは SQLite にキャッシュ
- 更新時に SSE で接続クライアントに通知

```python
# 主要な関数
start_collector()           # バックグラウンドスレッド開始
collect_all_data()          # 全ホストからデータ収集
collect_host_data(host)     # 特定ホストからデータ収集（手動更新用）
get_vm_info(vm_name)        # キャッシュから VM 情報取得
get_all_vm_info_for_host()  # ホストの全 VM 情報取得
get_uptime_info(host)       # 稼働時間情報取得
```

#### CPU ベンチマーク (`cpu_benchmark.py`)

cpubenchmark.net からスコアをスクレイピング:

- マルチスレッド/シングルスレッドスコアを取得
- ファジーマッチングで CPU 名を検索
- SQLite にキャッシュして再利用

#### キャッシュ管理 (`cache_manager.py`)

config.yaml のキャッシュを管理:

- 設定ファイル変更を検知して自動更新
- SQLite に JSON 形式で保存

#### SSE イベント通知

`my_lib.webapp.event` を使用:

```python
# データ更新時にクライアントへ通知
my_lib.webapp.event.notify_event(my_lib.webapp.event.EVENT_TYPE.DATA)
```

フロントエンドでは `useEventSource` フックで受信:

```typescript
useEventSource('/server-list/api/event', {
  onMessage: (event) => {
    if (event.data === 'data') {
      fetchData();  // データ再取得
    }
  },
});
```

### API エンドポイント

ベース URL: `/server-list/api`

| エンドポイント          | メソッド | 説明                               |
| ----------------------- | -------- | ---------------------------------- |
| `/config`               | GET      | サーバー設定 + VM 情報を取得       |
| `/vm/info`              | GET      | 単一 VM の詳細情報                 |
| `/vm/info/batch`        | POST     | 複数 VM の情報を一括取得           |
| `/vm/host/<esxi_host>`  | GET      | 指定ホストの全 VM 情報             |
| `/vm/refresh/<esxi>`    | POST     | 指定ホストのデータを即時更新       |
| `/cpu/benchmark`        | GET      | CPU ベンチマークスコア             |
| `/cpu/benchmark/batch`  | POST     | 複数 CPU のスコアを一括取得        |
| `/uptime`               | GET      | 全ホストの稼働時間                 |
| `/uptime/<host>`        | GET      | 指定ホストの稼働時間               |
| `/event`                | GET      | SSE でデータ更新を通知             |
| `/img/<filename>`       | GET      | サーバーモデル画像を提供           |

### 設定ファイル

#### config.yaml

```yaml
webapp:
  static_dir_path: frontend/dist
  title: Server List

machine:
  - name: server-1.example.com
    mode: ProLiant DL360 Gen10    # サーバーモデル名
    cpu: Intel Xeon Gold 6230
    ram: 256 GB
    os: ESXi 8.0                  # ESXi の場合、VM 情報を自動取得
    esxi: https://server-1.example.com/ui/
    ilo: https://server-1-ilo.example.com/
    storage:
      - name: SSD
        model: Samsung 980 PRO
        volume: 1 TB
```

#### secret.yaml

```yaml
esxi_auth:
  server-1.example.com:
    host: server-1.example.com
    username: root
    password: your_password
    port: 443
```

### SQLite データベース

2つのデータベースファイルを使用:

| ファイル            | 用途                              |
| ------------------- | --------------------------------- |
| `data/server_data.db` | VM 情報、稼働時間、取得ステータス |
| `data/cpu_spec.db`    | CPU ベンチマークスコア            |
| `data/cache.db`       | config.yaml キャッシュ            |

## デプロイ

### Docker

```bash
# フロントエンドビルド
cd frontend && npm run build && cd ..

# Docker Compose で起動
docker compose up --build
```

### Kubernetes

- `panel` namespace にデプロイ
- Liveness/Readiness Probe を設定
- ポート 5000 を公開

## 依存ライブラリ

### 主要な外部依存

| ライブラリ       | 用途                             |
| ---------------- | -------------------------------- |
| flask            | Web フレームワーク               |
| flask-cors       | CORS 対応                        |
| pyvmomi          | ESXi API クライアント            |
| beautifulsoup4   | CPU ベンチマークスクレイピング   |
| requests         | HTTP クライアント                |
| pyyaml           | 設定ファイル読み込み             |
| docopt           | CLI オプション解析               |
| pillow           | 画像処理                         |

### フロントエンド依存

| ライブラリ       | 用途                             |
| ---------------- | -------------------------------- |
| react            | UI フレームワーク                |
| react-router-dom | クライアントサイドルーティング   |
| bulma            | CSS フレームワーク               |
| vite             | ビルドツール                     |
| typescript       | 型付き JavaScript                |

### my-lib（自作共通ライブラリ）

| モジュール              | 用途                          |
| ----------------------- | ----------------------------- |
| my_lib.webapp.base      | Flask ブループリント          |
| my_lib.webapp.config    | Web アプリ設定管理            |
| my_lib.webapp.event     | SSE イベント通知              |
| my_lib.config           | YAML 設定読み込み             |
| my_lib.logger           | ロギング設定                  |

## コーディング規約

- Python 3.11+
- 型ヒントを積極的に使用
- ruff でフォーマット・lint
- pyright + mypy で型チェック

### インポートスタイル

`from xxx import yyy` は基本的に使わず、`import yyy` としてモジュールをインポートし、使用時は `yyy.xxx` の形式で参照する。

```python
# Good
import my_lib.webapp.event
my_lib.webapp.event.notify_event(...)

# Avoid
from my_lib.webapp.event import notify_event
notify_event(...)
```

**例外:**

- 標準ライブラリの一般的なパターン（例: `from pathlib import Path`）
- 型ヒント用のインポート（`from typing import TYPE_CHECKING`）
- dataclass などのデコレータ（`from dataclasses import dataclass`）
- Flask Blueprint（`from flask import Blueprint, jsonify, request`）

### 型チェック（pyright）

pyright のエラー対策として、各行に `# type: ignore` コメントを付けて回避するのは**最後の手段**とします。

基本方針:

1. **型推論が効くようにコードを書く** - 明示的な型注釈や適切な変数の初期化で対応
2. **型の絞り込み（Type Narrowing）を活用** - `assert`, `if`, `isinstance()` 等で型を絞り込む
3. **どうしても回避できない場合のみ `# type: ignore`** - その場合は理由をコメントに記載

```python
# Good: 型の絞り込み
value = get_optional_value()
assert value is not None
use_value(value)

# Avoid: type: ignore での回避
value = get_optional_value()
use_value(value)  # type: ignore
```

**例外:** テストコードでは、モックオブジェクトの使用など型チェックが困難な場合に `# type: ignore` を使用可能です。

### 型スタブがないライブラリへの対処

型スタブが提供されていないライブラリを使用する場合、`# type: ignore` コメントを大量に記述するのではなく、
戻り値を受け取る変数に `Any` 型注釈を付けて対処する：

```python
from typing import Any

# Good: Any 型注釈で型チェッカーに「このライブラリには型情報がない」ことを明示
si: Any = SmartConnect(host=host, user=username, pwd=password)

# Bad: 各行に type: ignore を記述
si = SmartConnect(...)  # type: ignore[no-untyped-call]
```

### ファイルの git add について

指示されて作成したプログラムやリファクタリングの結果追加されたプログラム以外は
git add しないこと。プログラムが動作するのに必要なデータについては、追加して良いか
確認すること。
