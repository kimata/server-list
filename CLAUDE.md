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
    ├── models.py               # データ構造定義（VMInfo, HostInfo 等の dataclass）
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
  # ESXi ホストの例
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

  # ZFS を使用するホストの例
  - name: storage-server.example.com
    mode: ProLiant ML110 Gen9
    cpu: Intel Xeon E5-2667 v4
    ram: 96 GB
    os: Linux
    filesystem:                   # Prometheus から収集するファイルシステム
      - zfs
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

### データ構造の定義

- API レスポンスや内部データ構造には dataclass を使用
- dict から dataclass を生成する `parse()` クラスメソッドを実装
- JSON シリアライズには `dataclasses.asdict()` を使用
- TypedDict は使用しない（dataclass を優先）

```python
from dataclasses import dataclass, asdict

@dataclass
class VMInfo:
    esxi_host: str
    vm_name: str
    cpu_count: int | None = None
    ram_mb: int | None = None

    @classmethod
    def parse(cls, data: dict) -> "VMInfo":
        return cls(
            esxi_host=data["esxi_host"],
            vm_name=data["vm_name"],
            cpu_count=data.get("cpu_count"),
            ram_mb=data.get("ram_mb"),
        )

# API レスポンスでの使用
return flask.jsonify({"success": True, "data": asdict(vm_info)})
```

### 例外ハンドリング

- 可能な限り具体的な例外クラスを指定（`sqlite3.Error`, `requests.RequestException` 等）
- `except Exception:` を使用する場合は理由をコメントで明記
- **例外を握りつぶす場合は必ずログ出力を追加**（`pass` のみは禁止）

```python
# Good: 具体的な例外クラス
try:
    response = requests.get(url, timeout=10)
except requests.RequestException as e:
    logging.warning("Failed to fetch %s: %s", url, e)
    return None

# 許容: pyVmomi など予期しない例外がある場合
try:
    vm_info = fetch_vm_data(vm)
except Exception:  # pyVmomi raises various exceptions
    logging.exception("Failed to fetch VM data")
    return None

# Good: 例外を握りつぶす場合はログ出力を追加
except (ValueError, TypeError) as e:
    logging.debug("Value conversion failed: %s", e)

# Bad: ログなしで pass（禁止）
except (ValueError, TypeError):
    pass  # <- CLAUDE.md 違反
```

### 重複コードの検出と統合

- **同じパターンが2回以上繰り返される場合は共通関数に抽出を検討**
- 特に以下のケースは統合を優先:
  - 類似した HTTP リクエスト処理
  - 類似したデータ収集ロジック
  - 同じエラーハンドリングパターン

```python
# Good: 共通ヘルパー関数を抽出
def _execute_prometheus_query(prometheus_url: str, query: str) -> dict | None:
    """Prometheus API 呼び出しの共通処理."""
    try:
        response = requests.get(...)
        ...
    except requests.RequestException as e:
        logging.warning("Prometheus query failed: %s", e)
        return None

def _fetch_prometheus_metric(prometheus_url: str, query: str) -> float | None:
    result = _execute_prometheus_query(prometheus_url, query)
    # 値の変換のみを担当
    ...

# Avoid: 同じHTTPリクエスト処理を複数関数で重複
def fetch_metric_a(...):
    response = requests.get(...)  # 重複
    ...

def fetch_metric_b(...):
    response = requests.get(...)  # 重複
    ...
```

### ログ出力

- print 文は使用禁止（デバッグ時も logging を使用）
- `logging.info()`, `logging.warning()`, `logging.error()`, `logging.exception()` を適切に使い分け

```python
# Good
logging.info("Starting data collection for %s", host)
logging.warning("Failed to fetch data: %s", error)

# Bad
print(f"Starting data collection for {host}")
```

### 後方互換性

- 後方互換性のためのモジュールレベル変数エクスポート（`DB_PATH = XXX` 等）は避ける
- テスト用のパス変更は getter/setter 関数で提供

```python
# Good: getter/setter パターン
_db_path = Path("./data/server_data.db")

def get_db_path() -> Path:
    return _db_path

def set_db_path(path: Path) -> None:
    global _db_path
    _db_path = path

# Bad: モジュールレベル変数のエクスポート
DB_PATH = Path("./data/server_data.db")  # テストで直接書き換えが必要になる
```

### 関数設計

- **関数は50行以内を目安とする** - 複雑な場合はヘルパー関数に分割
- **同じパターンが3回以上繰り返される場合は共通関数に抽出** - DRY 原則
- **深いネストは早期 return やガード節で回避** - 最大3段階を目安
- **walrus 演算子（`:=`）を活用** - 条件判定と値取得を同時に行う場合に有効

```python
# Good: 早期 return でネストを減らす
def process_data(data: dict | None) -> Result | None:
    if data is None:
        return None
    if not data.get("valid"):
        logging.warning("Invalid data")
        return None

    # メイン処理
    return Result(...)

# Avoid: 深いネスト
def process_data(data: dict | None) -> Result | None:
    if data is not None:
        if data.get("valid"):
            # メイン処理
            return Result(...)
        else:
            logging.warning("Invalid data")
    return None
```

```python
# Good: walrus 演算子で条件判定と値取得を同時に
def calculate_score(name: str) -> float:
    if (result := try_method_a(name)) is not None:
        return result
    if (result := try_method_b(name)) is not None:
        return result
    return default_method(name)

# Avoid: 一時変数を別途宣言
def calculate_score(name: str) -> float:
    result = try_method_a(name)
    if result is not None:
        return result
    result = try_method_b(name)
    if result is not None:
        return result
    return default_method(name)
```

### コードパターンの統一

- 同じ機能は同じ方法で実装（DRY 原則）
- 共通パターンは専用モジュールに集約（例: db_config.py でデータベースパス管理）
- API レスポンス形式は `{"success": bool, "data": ...}` で統一

### API レスポンス

全エンドポイントで統一された形式を使用:

```python
# 成功時
return flask.jsonify({
    "success": True,
    "data": dataclasses.asdict(result),
})

# エラー時（適切な HTTP ステータスコードを返す）
return flask.jsonify({
    "success": False,
    "error": "エラーメッセージ",
}), 404  # or 400, 500, etc.
```

### Prometheus 連携

- メトリクス取得は `_fetch_prometheus_metric()` ヘルパーを使用
- OS 固有処理（Linux/Windows）は引数で切り替え、関数は統合

```python
# Good: OS 固有処理を引数で切り替え
def fetch_prometheus_uptime(
    prometheus_url: str, instance: str, is_windows: bool = False
) -> dict | None:
    if is_windows:
        metric = f'windows_system_system_up_time{{instance=~"{instance}.*"}}'
    else:
        metric = f'node_boot_time_seconds{{instance=~"{instance}.*"}}'

    return _fetch_prometheus_metric_with_timestamp(prometheus_url, metric)

# Avoid: OS ごとに別関数
def fetch_prometheus_linux_uptime(...) -> dict | None:
    ...

def fetch_prometheus_windows_uptime(...) -> dict | None:
    ...
```

### 戻り値の型設計

- 複合データを返す関数は dataclass を使用（dict ではなく）
- `dict | list | None` のような複数型の戻り値は避ける
- キー別の専用 getter を提供して型を明確化

```python
# Good: 専用 getter で型を明確化
def get_config() -> dict | None:
    """config キャッシュを取得（型が明確）"""
    result = get_cache("config")
    return result if isinstance(result, dict) else None

# Avoid: 複数型の戻り値
def get_cache(key: str) -> dict | list | None:
    """汎用 getter（型が不明確）"""
    ...
```

### Protocol の使用

型スタブがないライブラリ（pyVmomi 等）には Protocol を定義して構造的部分型で対応:

- 必要なプロパティ/メソッドのみ定義
- `src/server_list/spec/protocols.py` に集約
- pyVmomi オブジェクトを扱う関数の型ヒントに使用

```python
# protocols.py
from typing import Protocol

class VirtualMachineProtocol(Protocol):
    """pyVmomi VirtualMachine の Protocol"""
    @property
    def name(self) -> str: ...
    @property
    def config(self) -> "VirtualMachineConfigProtocol | None": ...
    @property
    def summary(self) -> "VirtualMachineSummaryProtocol": ...

# 使用例
def process_vm(vm: VirtualMachineProtocol) -> str:
    return vm.name
```

### Protocol 導入の判断基準

Protocol の導入は以下の場合に限定する:

- 型スタブがないライブラリの主要な型を定義する場合
- 複数のモジュールで共有される型を定義する場合

以下の場合は Protocol を導入しない:

- `| None` 戻り値の削減が目的（外部 API 通信では None が適切）
- isinstance チェックの削減が目的（Protocol でも型ガードは必要）
- hasattr チェックの削減が目的（動的ライブラリでは必要）

### dict vs dataclass の使い分け

dataclass を使用する場合:

- API レスポンスの構造化データ
- モジュール間でやり取りするデータ
- IDE 補完や型チェックの恩恵を受けたい場合

dict のままで良い場合:

- 外部 YAML/JSON の読み込み結果（構造が不定）
- 内部ヘルパー関数の一時的なデータ
- 既存の型安全ラッパーが提供されている場合

### リファクタリング時の後方互換性

- **一時的なエイリアス関数は作成しない** - 呼び出し元を直接修正
- 移行期間が必要な場合は deprecation warning を追加

```python
# Avoid: 一時的なエイリアス関数
def get_uptime_info(host: str) -> dict | None:
    """Deprecated: Use get_host_info() instead."""
    return get_host_info(host)

# Good: 呼び出し元を直接修正するか、deprecation warning を追加
import warnings

def get_uptime_info(host: str) -> dict | None:
    warnings.warn(
        "get_uptime_info() is deprecated, use get_host_info() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_host_info(host)
```

### 未使用コードの削除

- **使用されていない Protocol / TypedDict / dataclass は削除する**
- 「将来使うかもしれない」コードは保持しない（YAGNI 原則）
- 削除時は grep で使用箇所がないことを確認

### 後方互換性コードの扱い

- **一時的なエイリアス関数は作成しない** - 呼び出し元を直接修正
- 外部公開 API の場合のみ deprecation warning を追加
- 内部使用のみの関数は警告なしで即座に置き換え

### 類似関数の実装パターン統一

- 同じデータ構造を返す関数は同じ型（dataclass）を使用
- 例: ストレージメトリクス取得関数は全て `StorageMetrics` を返す

### リファクタリングの判断基準

リファクタリングを実施する際は、以下の基準でメリット・デメリットを評価する：

**実施すべきケース:**

- CLAUDE.md の既存ルールに違反している場合
- 同じバグを複数箇所で修正する必要がある場合
- 型チェックエラーが発生している場合

**実施を見送るケース:**

- 変更量が多く、リスクが高い場合
- 現状で正常に動作しており、保守に問題がない場合
- 「将来のため」の予防的なリファクタリング（YAGNI 原則）

### ファイルの git add について

指示されて作成したプログラムやリファクタリングの結果追加されたプログラム以外は
git add しないこと。プログラムが動作するのに必要なデータについては、追加して良いか
確認すること。
