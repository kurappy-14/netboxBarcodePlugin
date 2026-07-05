# NetBox Barcode Plugin

NetBox にスマートフォン向けのバーコードスキャン画面を追加し、`CBL-` で始まるバーコードから Cable を照会するプラグインです。Cable の基本情報、A端/B端に分けた trace、末端接続先、カスタムフィールド `cable_status` を表示し、権限があるユーザーはステータスを更新できます。

## 対応バージョン

- NetBox: v4.6.1 を前提
- Python: 3.10 以降
- Django: 5.0.x
- 想定環境: netbox-docker などの NetBox Docker 環境

## インストール方法

1. NetBox 環境にこのリポジトリを配置、またはパッケージ化してインストールします。

   ```bash
   pip install /path/to/netboxBarcodePlugin
   ```

2. `configuration.py` でプラグインを有効化します。

   ```python
   PLUGINS = [
       "netbox_barcode_plugin",
   ]
   ```

3. NetBox を再起動し、静的ファイルを収集してください。

   ```bash
   python manage.py collectstatic --no-input
   ```

4. `/plugins/barcode/` にアクセスします。

## NetBox設定方法

### 必要なカスタムフィールド

NetBox 管理画面で **DCIM > Cable** を対象に以下を作成してください。

#### `barcode`

- name: `barcode`
- label: `バーコード`
- type: Text
- required: 任意
- 値例: `CBL-000001`

#### `cable_status`

- name: `cable_status`
- label: `ケーブルステータス`
- type: Selection
- required: 任意
- default: `not_created`

選択肢:

| value | label |
|---|---|
| `not_created` | `未作成` |
| `configured` | `作成済み` |
| `laid` | `敷設済み` |

`barcode` または `cable_status` が未作成の場合、API は設定不備を示す JSON エラーを返します。

### 権限設定

本プラグインは NetBox 標準の Object Permission を使用します。

- スキャン画面: ログイン済みユーザーがアクセス可能
- Cable照会: 対象 Cable に対する `dcim.view_cable` が必要
- ステータス更新: 対象 Cable に対する `dcim.change_cable` が必要
- スーパーユーザー: 常に更新可能

運用上、全ログインユーザーに Cable 閲覧を許可したい場合は、対象ユーザーまたはグループへ `dcim.view_cable` の Object Permission を付与してください。更新を許可するユーザーまたはグループには `dcim.change_cable` を付与してください。

## 使い方

1. NetBox にログインします。
2. `/plugins/barcode/` を開きます。
3. 「スキャン開始」を押し、スマートフォンの背面カメラで Code128 バーコードを読み取ります。
4. カメラが使えない場合は「手入力で検索」から同じ値を入力します。
5. Cable 情報、A端/B端 trace、末端接続先を確認します。
6. 更新権限がある場合のみ、ステータス選択と「更新」ボタンが表示されます。
7. 「再スキャン」を押した場合のみ次のスキャンを開始します。自動連続スキャンは行いません。

## API概要

すべての API はログイン済みセッションと CSRF トークンを前提とします。

### バーコード照会

```http
POST /plugins/barcode/api/lookup/
Content-Type: application/json
X-CSRFToken: <csrftoken>
```

```json
{
  "code": "CBL-000001"
}
```

主なレスポンス項目:

- `success`
- `type`
- `input`
- `cable`
- `matched_by`
- `can_update`
- `status_options`
- `trace`
- `endpoints`
- `trace_endpoints`
- `warnings`

検索仕様:

- `CBL-` プレフィックスのみ初期対応
- `Cable.label` は case-insensitive 完全一致
- `custom_field_data["barcode"]` も case-insensitive 完全一致
- 部分一致は禁止
- 入力値全体を検索に使用し、`CBL-` 後方だけを切り出しません
- 異なる Cable が複数一致した場合は `409 multiple_cables_found`

### ケーブルステータス更新

```http
POST /plugins/barcode/api/cables/<cable_id>/status/
Content-Type: application/json
X-CSRFToken: <csrftoken>
```

```json
{
  "cable_status": "laid"
}
```

更新対象は `custom_field_data["cable_status"]` のみです。NetBox の `change_logging` コンテキストで保存し、Changelog にユーザー操作ログを記録します。

## html5-qrcode のローカル配置について

バーコード読み取りには `html5-qrcode` v2.3.8 を使用し、以下に同梱しています。

```text
netbox_barcode_plugin/static/netbox_barcode_plugin/js/html5-qrcode.min.js
```

実行時に外部CDNから読み込まないため、閉域環境でも利用できます。第三者ライセンスは `THIRD_PARTY_LICENSES.md` を参照してください。

## テスト実行方法

NetBox v4.6.1 のテスト環境で以下を実行してください。

```bash
pytest netbox_barcode_plugin/tests/
```

このリポジトリ単体の軽量確認としては、Python構文チェックや静的ファイル検査を実行できます。

```bash
python -m compileall netbox_barcode_plugin
pytest netbox_barcode_plugin/tests/test_static_assets.py netbox_barcode_plugin/tests/test_license_files.py
```

## ライセンス

本プラグインは MIT License です。詳細は `LICENSE` を参照してください。

## 第三者ライセンスについて

同梱している `html5-qrcode` は Apache License 2.0 です。詳細は `THIRD_PARTY_LICENSES.md` を参照してください。
