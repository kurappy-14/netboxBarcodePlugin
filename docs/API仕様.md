# API仕様.md

# NetBox Barcode Plugin API仕様

## 1. 概要

本ドキュメントは、`netbox_barcode_plugin` が提供する画面表示エンドポイントおよびJSON APIエンドポイントの仕様を定義する。

本プラグインは、スマートフォン等で読み取ったバーコード値をもとにNetBox上のCableを検索し、接続情報、配線経路、現在のケーブルステータス、更新可否を返す。  
また、権限を持つユーザーに対してCableのカスタムフィールド `cable_status` の更新APIを提供する。

---

## 2. 基本URL

NetBoxプラグインのbase URLは以下とする。

```text
/plugins/barcode/
```

JSON APIは以下の配下に配置する。

```text
/plugins/barcode/api/
```

---

## 3. エンドポイント一覧

| 種別 | Method | URL | URL name | 内容 |
|---|---|---|---|---|
| 画面 | GET | `/plugins/barcode/` | `scan` | バーコードスキャン画面表示 |
| API | POST | `/plugins/barcode/api/lookup/` | `api_lookup` | バーコード照会 |
| API | POST | `/plugins/barcode/api/cables/<cable_id>/status/` | `api_cable_status_update` | ケーブルステータス更新 |

---

## 4. 共通仕様

### 4.1 認証

すべての画面およびAPIは、NetBoxの標準セッション認証を使用する。

未ログインユーザーは利用できない。

JSON APIへの未ログインアクセス時は、NetBox/Djangoの標準挙動に従い、ログイン画面へのリダイレクトまたは403相当の応答となる。

---

### 4.2 CSRF

`POST` APIではDjangoのCSRF保護を有効にする。

Fetch APIから呼び出す場合は、CookieからCSRFトークンを取得し、以下のヘッダーに含めること。

```http
X-CSRFToken: <csrftoken>
```

---

### 4.3 共通リクエストヘッダー

JSON APIでは原則として以下のヘッダーを使用する。

```http
Content-Type: application/json
Accept: application/json
X-CSRFToken: <csrftoken>
```

Fetch APIでは、NetBoxのログインセッションCookieを送信するため、以下を指定する。

```javascript
credentials: 'same-origin'
```

---

### 4.4 共通成功レスポンス

成功時はJSONで以下のフィールドを含める。

| field | type | required | 内容 |
|---|---|---|---|
| `success` | boolean | yes | 成功時は常に `true` |

---

### 4.5 共通エラーレスポンス

エラー時は以下のJSON形式に統一する。

```json
{
  "success": false,
  "error": "人間向けエラーメッセージ",
  "code": "machine_readable_error_code"
}
```

| field | type | required | 内容 |
|---|---|---|---|
| `success` | boolean | yes | エラー時は常に `false` |
| `error` | string | yes | UI表示用の人間向けエラーメッセージ |
| `code` | string | yes | 機械処理向けエラーコード。英語snake_case |

---

### 4.6 共通HTTPステータスコード

| HTTPステータス | 用途 |
|---:|---|
| `200` | 正常終了 |
| `400` | 不正なJSON、不正な入力値、空文字、最大長超過、不正なステータス値 |
| `403` | 権限なし |
| `404` | 対象Cableなし |
| `409` | 複数Cable一致 |
| `405` | 許可されていないHTTPメソッド |
| `500` | 想定外エラー、必須カスタムフィールド未設定などのサーバー側設定不備 |

---

### 4.7 共通エラーコード

| code | HTTPステータス | 内容 |
|---|---:|---|
| `invalid_json` | 400 | JSONとして解釈できない |
| `missing_code` | 400 | バーコード値が未指定 |
| `invalid_barcode` | 400 | バーコード値が空、または不正 |
| `barcode_too_long` | 400 | バーコード値が最大長を超過 |
| `invalid_prefix` | 400 | 未対応のプレフィックス |
| `cable_not_found` | 404 | 対象Cableが存在しない |
| `multiple_cables_found` | 409 | 複数のCableが一致 |
| `permission_denied` | 403 | 閲覧または更新権限なし |
| `invalid_status` | 400 | 不正な `cable_status` |
| `custom_field_not_configured` | 500 | 必須カスタムフィールド未設定 |
| `method_not_allowed` | 405 | 許可されていないHTTPメソッド |
| `internal_error` | 500 | 想定外エラー |

---

## 5. 共通データ型

### 5.1 ObjectRef

trace結果や接続先を表現する共通オブジェクト形式。

```json
{
  "name": "Switch01 GigabitEthernet1/0/1",
  "type": "interface",
  "device": "Switch01",
  "url": "/dcim/interfaces/10/"
}
```

| field | type | required | 内容 |
|---|---|---|---|
| `name` | string | yes | 表示名 |
| `type` | string | yes | `interface` / `frontport` / `rearport` / `cable` 等の種別 |
| `device` | string/null | yes | デバイス名。該当しない場合は `null` |
| `url` | string/null | yes | NetBox標準の詳細URL。取得できない場合は `null` |

---

### 5.2 CableStatus

Cableのカスタムフィールド `cable_status` を表現する形式。

```json
{
  "value": "configured",
  "label": "作成済み",
  "is_defaulted": false
}
```

| field | type | required | 内容 |
|---|---|---|---|
| `value` | string | yes | `not_created` / `configured` / `laid` |
| `label` | string | yes | `未作成` / `作成済み` / `敷設済み` |
| `is_defaulted` | boolean | yes | 未設定値を表示上のデフォルトとして扱った場合は `true` |

`custom_field_data["cable_status"]` が未設定、空文字、または `null` の場合、照会API上は以下として扱う。

```json
{
  "value": "not_created",
  "label": "未作成",
  "is_defaulted": true
}
```

ただし、照会APIではCableオブジェクトを保存しない。  
未設定値を自動保存してはならない。

---

### 5.3 StatusOption

UI表示用のステータス選択肢。

```json
{
  "value": "laid",
  "label": "敷設済み"
}
```

固定で以下の3値を返す。

```json
[
  {
    "value": "not_created",
    "label": "未作成"
  },
  {
    "value": "configured",
    "label": "作成済み"
  },
  {
    "value": "laid",
    "label": "敷設済み"
  }
]
```

---

### 5.4 CableObject

Cable情報の共通形式。

```json
{
  "id": 123,
  "label": "CBL-000001",
  "display": "CBL-000001",
  "url": "/dcim/cables/123/",
  "barcode": "CBL-000001",
  "status": {
    "value": "configured",
    "label": "作成済み",
    "is_defaulted": false
  }
}
```

| field | type | required | 内容 |
|---|---|---|---|
| `id` | integer | yes | Cable ID |
| `label` | string/null | yes | `Cable.label` |
| `display` | string | yes | UI表示用のCable名 |
| `url` | string/null | yes | NetBox標準のCable詳細URL |
| `barcode` | string/null | yes | `custom_field_data["barcode"]` |
| `status` | object | yes | 現在のケーブルステータス |

---

## 6. 画面表示エンドポイント

# 6.1 スキャン画面表示

## Endpoint

```http
GET /plugins/barcode/
```

## URL name

```text
scan
```

## 用途

バーコードスキャン画面を表示する。

## 認証

ログイン済みユーザーのみアクセス可能。

## レスポンス

HTMLを返す。

## 備考

このエンドポイントはJSON APIではない。  
NetBoxの `base/layout.html` を継承したスキャン画面テンプレートを返す。

---

## 7. JSON APIエンドポイント

# 7.1 バーコード照会API

## Endpoint

```http
POST /plugins/barcode/api/lookup/
```

## URL name

```text
api_lookup
```

## 用途

スキャンまたは手入力されたバーコード値をもとに対象オブジェクトを検索し、接続情報、配線経路、現在のステータス、更新可否を返す。

初期実装では `CBL-` プレフィックスのみ対応し、Cable検索へルーティングする。

将来的に `DEV-` 等のプレフィックスを追加できるよう、プレフィックスディスパッチャー方式で実装する。

---

## リクエストJSON

```json
{
  "code": "CBL-000001"
}
```

## Request fields

| field | type | required | 内容 |
|---|---|---|---|
| `code` | string | yes | スキャンまたは手入力されたバーコード値 |

---

## 入力値バリデーション

`code` には以下のルールを適用する。

1. `code` が存在しない場合は400エラー
2. `code` が文字列でない場合は400エラー
3. 前後の空白を除去する
4. 前後空白除去後に空文字の場合は400エラー
5. 最大長は128文字
6. 128文字を超える場合は400エラー
7. 大文字小文字は区別しない
8. `CBL-` から始まる場合のみCable検索へルーティングする
9. `CBL-` の後ろだけを切り出さず、スキャン値全体を検索に使用する
10. 文字種の正規表現制限は設けない

---

## 正規化仕様

入力値:

```json
{
  "code": " cbl-000001 "
}
```

正規化後:

```text
cbl-000001
```

プレフィックス判定時:

```text
CBL-000001
```

検索はcase-insensitive exact matchで行う。

レスポンスの `normalized_code` は、前後空白除去後の値を返す。  
大文字小文字は、原則として入力値の表記を保持してよい。

---

## Cable検索仕様

`CBL-` プレフィックスの場合、以下の条件でCableを検索する。

検索対象:

- `Cable.label`
- `Cable.custom_field_data["barcode"]`

検索条件:

- case-insensitive exact match
- 部分一致検索は行わない
- スキャン値全体を使用する

`label` と `custom_field_data["barcode"]` の両方に一致した場合でも、同一Cableであれば1件として扱う。

異なるCableが2件以上一致した場合は、最初の1件を返さず409エラーを返す。

---

## 必須カスタムフィールド確認

照会APIでは、以下のカスタムフィールドが存在することを確認する。

- `barcode`
- `cable_status`

存在しない場合は、500エラーとして `custom_field_not_configured` を返す。

ただし、対象Cableの `barcode` 値が未設定であること自体はエラーではない。

---

## 権限判定

対象Cableが1件に確定した後、閲覧権限を判定する。

閲覧可否:

- 対象Cableに対して `dcim.view_cable` 権限を持つ場合のみ詳細情報を返す
- 権限がない場合は403エラーを返す

更新可否:

- スーパーユーザーは常に `can_update: true`
- 一般ユーザーは対象Cableに対して `dcim.change_cable` 権限を持つ場合のみ `can_update: true`
- それ以外は `can_update: false`

---

## 成功レスポンスJSON

```json
{
  "success": true,
  "type": "cable",
  "input": {
    "code": " CBL-000001 ",
    "normalized_code": "CBL-000001",
    "prefix": "CBL"
  },
  "cable": {
    "id": 123,
    "label": "CBL-000001",
    "display": "CBL-000001",
    "url": "/dcim/cables/123/",
    "barcode": "CBL-000001",
    "status": {
      "value": "configured",
      "label": "作成済み",
      "is_defaulted": false
    }
  },
  "matched_by": [
    "label"
  ],
  "can_update": true,
  "status_options": [
    {
      "value": "not_created",
      "label": "未作成"
    },
    {
      "value": "configured",
      "label": "作成済み"
    },
    {
      "value": "laid",
      "label": "敷設済み"
    }
  ],
  "trace": {
    "a_side": [
      {
        "name": "Patch Panel 01 Front Port 01",
        "type": "frontport",
        "device": "Patch Panel 01",
        "url": "/dcim/front-ports/1/"
      },
      {
        "name": "Switch01 GigabitEthernet1/0/1",
        "type": "interface",
        "device": "Switch01",
        "url": "/dcim/interfaces/10/"
      }
    ],
    "b_side": [
      {
        "name": "Server01 eth0",
        "type": "interface",
        "device": "Server01",
        "url": "/dcim/interfaces/20/"
      }
    ]
  },
  "endpoints": {
    "a_side": {
      "name": "Switch01 GigabitEthernet1/0/1",
      "type": "interface",
      "device": "Switch01",
      "url": "/dcim/interfaces/10/"
    },
    "b_side": {
      "name": "Server01 eth0",
      "type": "interface",
      "device": "Server01",
      "url": "/dcim/interfaces/20/"
    }
  },
  "warnings": []
}
```

---

## 成功レスポンス fields

### Root fields

| field | type | required | 内容 |
|---|---|---|---|
| `success` | boolean | yes | 常に `true` |
| `type` | string | yes | 対象種別。初期実装では `cable` |
| `input` | object | yes | 入力値情報 |
| `cable` | object | yes | Cable情報 |
| `matched_by` | array[string] | yes | 一致した検索対象 |
| `can_update` | boolean | yes | ステータス更新可否 |
| `status_options` | array[object] | yes | UI表示用ステータス選択肢 |
| `trace` | object | yes | A端/B端の配線経路 |
| `endpoints` | object | yes | A端/B端の最終接続先 |
| `warnings` | array[string] | yes | 警告メッセージ。警告なしの場合は空配列 |

---

### `input`

| field | type | required | 内容 |
|---|---|---|---|
| `code` | string | yes | APIに渡された元の入力値 |
| `normalized_code` | string | yes | 前後空白除去後の値 |
| `prefix` | string | yes | 判定されたプレフィックス。例: `CBL` |

---

### `matched_by`

検索一致箇所を配列で返す。

指定可能な値:

```text
label
barcode
```

例:

```json
{
  "matched_by": ["label"]
}
```

`label` と `barcode` の両方が同一Cableに一致した場合:

```json
{
  "matched_by": ["label", "barcode"]
}
```

---

### `trace`

Cableのtrace結果は、A端側とB端側を分けて返す。

```json
{
  "trace": {
    "a_side": [],
    "b_side": []
  }
}
```

| field | type | required | 内容 |
|---|---|---|---|
| `a_side` | array[ObjectRef] | yes | A端側の経路 |
| `b_side` | array[ObjectRef] | yes | B端側の経路 |

未接続の端は空配列とする。  
未接続はエラー扱いしない。

---

### `endpoints`

A端/B端それぞれの最終接続先を返す。

```json
{
  "endpoints": {
    "a_side": {
      "name": "Switch01 GigabitEthernet1/0/1",
      "type": "interface",
      "device": "Switch01",
      "url": "/dcim/interfaces/10/"
    },
    "b_side": null
  }
}
```

| field | type | required | 内容 |
|---|---|---|---|
| `a_side` | ObjectRef/null | yes | A端側の最終接続先 |
| `b_side` | ObjectRef/null | yes | B端側の最終接続先 |

未接続の場合は `null` とする。

---

## 照会APIエラー例

### 不正JSON

HTTPステータス: `400`

```json
{
  "success": false,
  "error": "リクエストJSONを解析できません。",
  "code": "invalid_json"
}
```

---

### `code` 未指定

HTTPステータス: `400`

```json
{
  "success": false,
  "error": "バーコード値が指定されていません。",
  "code": "missing_code"
}
```

---

### `code` が文字列でない

HTTPステータス: `400`

```json
{
  "success": false,
  "error": "バーコード値は文字列で指定してください。",
  "code": "invalid_barcode"
}
```

---

### 空文字

HTTPステータス: `400`

```json
{
  "success": false,
  "error": "バーコード値が空です。",
  "code": "invalid_barcode"
}
```

---

### 最大長超過

HTTPステータス: `400`

```json
{
  "success": false,
  "error": "バーコード値が長すぎます。128文字以内で指定してください。",
  "code": "barcode_too_long"
}
```

---

### 未対応プレフィックス

HTTPステータス: `400`

```json
{
  "success": false,
  "error": "未対応のバーコードプレフィックスです。",
  "code": "invalid_prefix"
}
```

---

### Cableなし

HTTPステータス: `404`

```json
{
  "success": false,
  "error": "対象のケーブルが見つかりません。",
  "code": "cable_not_found"
}
```

---

### 複数Cable一致

HTTPステータス: `409`

```json
{
  "success": false,
  "error": "複数のケーブルが一致しました。バーコードまたはラベルの重複を確認してください。",
  "code": "multiple_cables_found",
  "matches_count": 2
}
```

`matches_count` は任意フィールドとする。

重複したCableのIDやURLは、誤操作防止および情報漏えい防止のため原則として返さない。

---

### 閲覧権限なし

HTTPステータス: `403`

```json
{
  "success": false,
  "error": "このケーブルを閲覧する権限がありません。",
  "code": "permission_denied"
}
```

---

### 必須カスタムフィールド未設定

HTTPステータス: `500`

```json
{
  "success": false,
  "error": "必須カスタムフィールド 'cable_status' が設定されていません。",
  "code": "custom_field_not_configured"
}
```

---

# 7.2 ケーブルステータス更新API

## Endpoint

```http
POST /plugins/barcode/api/cables/<cable_id>/status/
```

## URL name

```text
api_cable_status_update
```

## 用途

指定したCableのカスタムフィールド `cable_status` の値を更新する。

更新対象は `cable_status` のみとする。  
Cableのその他のフィールドは更新しない。

---

## Path parameters

| parameter | type | required | 内容 |
|---|---|---|---|
| `cable_id` | integer | yes | 更新対象のCable ID |

---

## リクエストJSON

```json
{
  "cable_status": "laid"
}
```

## Request fields

| field | type | required | 内容 |
|---|---|---|---|
| `cable_status` | string | yes | 更新後のステータス値 |

---

## 指定可能な `cable_status`

| value | label |
|---|---|
| `not_created` | `未作成` |
| `configured` | `作成済み` |
| `laid` | `敷設済み` |

上記以外の値が指定された場合は400エラーを返す。

ステータス遷移の制限は行わない。  
更新権限を持つユーザーであれば、どの状態からどの状態へも自由に変更できる。

---

## 必須カスタムフィールド確認

更新APIでは、以下のカスタムフィールドが存在することを確認する。

- `cable_status`

存在しない場合は、500エラーとして `custom_field_not_configured` を返す。

---

## 権限判定

更新可否は以下の通りとする。

- スーパーユーザーは常に更新可能
- 一般ユーザーは、対象Cableに対して `dcim.change_cable` 権限を持つ場合のみ更新可能

権限がない場合は403エラーを返す。

---

## 更新処理

更新時は以下を満たすこと。

1. 対象Cableを取得する
2. `cable_status` の値を検証する
3. 更新権限を判定する
4. 更新前の `cable_status` を取得する
5. `custom_field_data["cable_status"]` に新しい値を設定する
6. NetBox標準のバリデーションを通す
7. NetBox標準の `change_logging` コンテキストマネージャを使用して保存する
8. Changelogにユーザーの操作ログを記録する
9. 更新後のステータスをJSONで返す

同時更新時の排他制御は行わない。  
標準仕様として後勝ちとする。

---

## 成功レスポンスJSON

```json
{
  "success": true,
  "message": "更新しました。",
  "cable": {
    "id": 123,
    "label": "CBL-000001",
    "display": "CBL-000001",
    "url": "/dcim/cables/123/",
    "barcode": "CBL-000001",
    "status": {
      "value": "laid",
      "label": "敷設済み",
      "is_defaulted": false
    }
  },
  "updated": {
    "field": "cable_status",
    "old": {
      "value": "configured",
      "label": "作成済み"
    },
    "new": {
      "value": "laid",
      "label": "敷設済み"
    }
  },
  "can_update": true
}
```

---

## 成功レスポンス fields

### Root fields

| field | type | required | 内容 |
|---|---|---|---|
| `success` | boolean | yes | 常に `true` |
| `message` | string | yes | UI表示用メッセージ |
| `cable` | object | yes | 更新後のCable情報 |
| `updated` | object | yes | 更新内容 |
| `can_update` | boolean | yes | 更新後時点での更新可否 |

---

### `updated`

| field | type | required | 内容 |
|---|---|---|---|
| `field` | string | yes | 更新対象フィールド。常に `cable_status` |
| `old` | object | yes | 更新前ステータス |
| `new` | object | yes | 更新後ステータス |

---

### `updated.old` / `updated.new`

| field | type | required | 内容 |
|---|---|---|---|
| `value` | string | yes | ステータス値 |
| `label` | string | yes | 表示名 |

---

## 更新APIエラー例

### 不正JSON

HTTPステータス: `400`

```json
{
  "success": false,
  "error": "リクエストJSONを解析できません。",
  "code": "invalid_json"
}
```

---

### `cable_status` 未指定

HTTPステータス: `400`

```json
{
  "success": false,
  "error": "ケーブルステータスが指定されていません。",
  "code": "invalid_status",
  "allowed_values": [
    "not_created",
    "configured",
    "laid"
  ]
}
```

---

### 不正なステータス値

HTTPステータス: `400`

```json
{
  "success": false,
  "error": "不正なケーブルステータスです。",
  "code": "invalid_status",
  "allowed_values": [
    "not_created",
    "configured",
    "laid"
  ]
}
```

---

### 対象Cableなし

HTTPステータス: `404`

```json
{
  "success": false,
  "error": "対象のケーブルが見つかりません。",
  "code": "cable_not_found"
}
```

---

### 更新権限なし

HTTPステータス: `403`

```json
{
  "success": false,
  "error": "このケーブルを更新する権限がありません。",
  "code": "permission_denied"
}
```

---

### 必須カスタムフィールド未設定

HTTPステータス: `500`

```json
{
  "success": false,
  "error": "必須カスタムフィールド 'cable_status' が設定されていません。",
  "code": "custom_field_not_configured"
}
```

---

## 8. フロントエンドからの呼び出し例

### 8.1 CSRFトークン取得関数

```javascript
function getCookie(name) {
  const cookies = document.cookie ? document.cookie.split(';') : [];

  for (const cookie of cookies) {
    const trimmed = cookie.trim();

    if (trimmed.startsWith(name + '=')) {
      return decodeURIComponent(trimmed.substring(name.length + 1));
    }
  }

  return null;
}
```

---

### 8.2 照会API呼び出し例

```javascript
async function lookupBarcode(code) {
  const response = await fetch('/plugins/barcode/api/lookup/', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({ code })
  });

  return await response.json();
}
```

---

### 8.3 ステータス更新API呼び出し例

```javascript
async function updateCableStatus(cableId, cableStatus) {
  const response = await fetch(`/plugins/barcode/api/cables/${cableId}/status/`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({
      cable_status: cableStatus
    })
  });

  return await response.json();
}
```

---

## 9. 実装上の注意

### 9.1 プレフィックスディスパッチャー

`/plugins/barcode/api/lookup/` は、入力値のプレフィックスを判定して処理を分岐する。

初期実装では以下のみ対応する。

| prefix | type | handler |
|---|---|---|
| `CBL-` | `cable` | Cable検索処理 |

将来的に以下のような拡張を可能にする。

| prefix | type | handler |
|---|---|---|
| `DEV-` | `device` | Device検索処理 |
| `RCK-` | `rack` | Rack検索処理 |

---

### 9.2 情報漏えい防止

権限がないユーザーに対して、Cableの詳細情報、trace情報、接続先情報を返してはならない。

対象Cableが1件に確定した後、`dcim.view_cable` 権限がない場合は403を返す。

複数Cable一致時は、原則として一致したCableのID、label、URLなどの詳細情報は返さない。

---

### 9.3 ステータス更新UIとの連携

照会APIの `can_update` が `true` の場合のみ、フロントエンドはステータス更新用ドロップダウンと更新ボタンを表示する。

`can_update` が `false` の場合は、現在のステータスをテキスト表示のみとし、更新操作UIは表示しない。

---

### 9.4 未接続Cableの扱い

Cableの片端または両端が未接続であってもエラー扱いしない。

- trace配列は空配列
- endpointは `null`

として返す。

---

### 9.5 `cable_status` 未設定時の扱い

照会時に `cable_status` が未設定の場合は、表示上は `not_created` として扱う。

ただし、照会APIでは保存しない。

明示的に保存したい場合は、更新APIで以下を送信する。

```json
{
  "cable_status": "not_created"
}
```

---

### 9.6 UI表示言語

APIの `error`、`message`、ステータスラベルは日本語とする。

APIの `code` は英語snake_caseとする。

---

## 10. API仕様まとめ

### 画面表示

```http
GET /plugins/barcode/
```

- ログイン済みユーザーのみ利用可能
- HTMLを返す

---

### バーコード照会

```http
POST /plugins/barcode/api/lookup/
```

リクエスト:

```json
{
  "code": "CBL-000001"
}
```

主な成功レスポンス:

```json
{
  "success": true,
  "type": "cable",
  "cable": {
    "id": 123,
    "label": "CBL-000001",
    "display": "CBL-000001",
    "url": "/dcim/cables/123/",
    "barcode": "CBL-000001",
    "status": {
      "value": "configured",
      "label": "作成済み",
      "is_defaulted": false
    }
  },
  "can_update": true,
  "trace": {
    "a_side": [],
    "b_side": []
  },
  "endpoints": {
    "a_side": null,
    "b_side": null
  }
}
```

---

### ケーブルステータス更新

```http
POST /plugins/barcode/api/cables/<cable_id>/status/
```

リクエスト:

```json
{
  "cable_status": "laid"
}
```

主な成功レスポンス:

```json
{
  "success": true,
  "message": "更新しました。",
  "cable": {
    "id": 123,
    "label": "CBL-000001",
    "display": "CBL-000001",
    "url": "/dcim/cables/123/",
    "barcode": "CBL-000001",
    "status": {
      "value": "laid",
      "label": "敷設済み",
      "is_defaulted": false
    }
  },
  "updated": {
    "field": "cable_status",
    "old": {
      "value": "configured",
      "label": "作成済み"
    },
    "new": {
      "value": "laid",
      "label": "敷設済み"
    }
  },
  "can_update": true
}
```