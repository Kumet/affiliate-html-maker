# affiliate-html-maker

テキストを貼り付けるだけで、商品一覧HTMLを生成してプレビューし、そのままダウンロードできる FastAPI アプリです。

## セットアップ

```bash
uv sync
```

## 開発サーバ

```bash
uv run uvicorn app.main:app --reload
```

## テスト

```bash
uv run pytest
```

## Render デプロイ

このリポジトリには Render 用の [render.yaml](/Users/kume/VSCodeProjects/affiliate-html-maker/render.yaml) と [requirements.txt](/Users/kume/VSCodeProjects/affiliate-html-maker/requirements.txt) を追加済みです。

### いちばん簡単な方法

1. Render にログイン
2. `New +` から `Blueprint` を選ぶ
3. `Kumet/affiliate-html-maker` を選ぶ
4. `render.yaml` を読ませて作成する
5. 数分待って `https://<service-name>.onrender.com` にアクセスする

### Render 側で作られる設定

- `plan`: `free`
- `buildCommand`: `pip install -r requirements.txt`
- `startCommand`: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- 環境変数:
  - `APP_NAME=Affiliate HTML Maker`
  - `AFFILIATE_TAG=costco-item-22`

### Blueprint を使わない場合

`New +` → `Web Service` で GitHub リポジトリを選び、以下を入力します。

- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Instance Type: `Free`

無料枠ではスリープ復帰時に初回表示が少し遅くなります。

## 毎回そのまま使える更新手順メモ

### 1. ローカルで修正する

必要なファイルを編集します。

### 2. 動作確認する

```bash
uv run ruff check
uv run pytest -q
```

必要なら開発サーバも確認します。

```bash
uv run uvicorn app.main:app --reload
```

### 3. GitHub に反映する

```bash
git status
git add .
git commit -m "fix: 修正内容を一言で"
git push origin main
```

### 4. Render の自動デプロイを待つ

`main` に push すると Render が自動で再デプロイします。

- Render の対象サービスを開く
- `Deploys` または `Events` を見る
- `Live` になれば反映完了

### 5. もし自動デプロイされない場合

Render で手動実行します。

1. 対象サービスを開く
2. `Manual Deploy` を押す
3. `Deploy latest commit` を選ぶ

### 6. 変更後の確認ポイント

- トップページが開く
- プレビュー更新が動く
- HTML ダウンロードが動く
- 追加した環境変数がある場合は Render 側にも設定したか確認する

### 最短コマンド

```bash
uv run ruff check
uv run pytest -q
git add .
git commit -m "fix: 修正内容"
git push origin main
```

## 主な構成

- `app/services/text_parser.py`: 入力テキストをセクションと商品カードに分解
  セクション見出しは入力テキストに含まれる場合のみ出力
- `app/services/html_builder.py`: Jinja2 でカードHTMLを構築
- `app/routers/`: 画面表示、HTMXプレビュー、ダウンロードの各エンドポイント
- `tests/`: パーサ、HTML生成、HTTPレスポンスの検証
