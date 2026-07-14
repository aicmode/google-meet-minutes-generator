# Google Meet 議事録自動生成ツール

Google Meet の録音データから議事録を自動生成し、Google ドキュメントへ保存するツールです。

## 処理の流れ

```
録音ファイル (recordings/)
      │
      ▼
① Whisper API で文字起こし ......... transcribe.py
      │
      ▼
② OpenAI API で議事録を生成 ........ summarize.py
      │
      ▼
③ Google Docs API でドキュメント作成
   & 議事録を書き込み ............... google_docs.py
      │
      ▼
④ (任意)Google Drive API で
   指定フォルダへ移動 ............... google_docs.py
```

## 使用技術

| 技術 | 用途 |
|---|---|
| Python 3.9+ | 実装言語 |
| OpenAI Whisper API | 音声の文字起こし |
| OpenAI API (ChatGPT) | 議事録の生成 |
| Google Docs API | ドキュメントの作成・書き込み |
| Google Drive API | ドキュメントのフォルダ移動 |
| python-dotenv | APIキーなどの環境変数管理 |

## プロジェクト構成

```
google-meet-minutes-generator/
├── main.py            # メインスクリプト(全体の流れを制御)
├── transcribe.py      # Whisper API による文字起こし
├── summarize.py       # OpenAI API による議事録生成
├── google_docs.py     # Google Docs / Drive API の操作
├── config.py          # 環境変数・設定値の管理
├── requirements.txt   # 依存ライブラリ一覧
├── .env.example       # 環境変数のテンプレート
├── .gitignore         # Git 管理から除外するファイル
└── recordings/        # 録音ファイルを置くフォルダ
```

## セットアップ

### 1. リポジトリの取得と依存ライブラリのインストール

```bash
git clone <このリポジトリのURL>
cd google-meet-minutes-generator

# 仮想環境の作成(推奨)
python3 -m venv venv
source venv/bin/activate  # Windows は venv\Scripts\activate

# ライブラリのインストール
pip install -r requirements.txt
```

### 2. OpenAI APIキーの取得

1. [OpenAI Platform](https://platform.openai.com/) にログインする
2. 必要に応じて Billing で支払い方法や利用上限を設定する
3. [API Keys](https://platform.openai.com/api-keys) で「Create new secret key」を選ぶ
4. 表示されたキーを安全な場所に一度だけ控える（他人に共有しない）
5. `.env.example` をコピーして `.env` を作り、キーを設定する

```bash
cp .env.example .env
```

```dotenv
OPENAI_API_KEY=ここに発行したAPIキー
```

ChatGPT の有料プランと OpenAI API の料金・請求は別です。APIを利用できる状態か
OpenAI Platform 側で確認してください。`.env` は Git の管理対象にしないでください。

### 3. Google API の設定

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成する
2. 画面上部で作成したプロジェクトを選択する
3. 「APIとサービス」→「ライブラリ」で以下を検索し、それぞれ「有効にする」を押す
   - **Google Docs API**
   - **Google Drive API**
4. 「APIとサービス」→「OAuth 同意画面」でアプリ情報を設定する
5. 公開ステータスがテストの場合は、同意画面の「テストユーザー」に利用する
   Google アカウントを追加する
6. 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuth クライアント ID」
   - アプリケーションの種類: **デスクトップアプリ**
7. 作成後に JSON をダウンロードする
8. ダウンロードした JSON を `credentials.json` に名前変更し、`main.py` と同じ
   プロジェクト直下へ置く（JSONの中身を手作業で書き換える必要はありません）

### 4. 環境変数の設定

すでに `.env` を作成済みなら、そのファイルを開いて APIキーを設定します。

```
OPENAI_API_KEY=sk-xxxxxxxxxxxx
```

## 実行方法

Google Meet の録音ファイル(mp3 / mp4 / m4a / wav / webm など)を `recordings/` に置いて実行します。

例: ダウンロードした `meeting.mp4` を Finder またはエクスプローラーで
`recordings` フォルダへ移動します。25MBを超えるファイルは事前に分割または圧縮してください。

```bash
# ファイルを指定して実行
python main.py recordings/meeting.mp3

# ファイルを省略すると recordings/ 内の最新ファイルを自動選択
python main.py
```

初回実行時はブラウザが開きます。Google Cloud のテストユーザーに登録したアカウントで
ログインし、Google Docs / Drive へのアクセスを許可してください。認証完了後はブラウザを
閉じてターミナルへ戻ります。認証結果は `token.json` に保存され、2回目以降は自動で
再利用されます。`token.json` も秘密情報なので共有・コミットしないでください。

### 実行例

```
2026-07-14 11:00:00 [INFO] ===== ステップ1/3: 文字起こし =====
2026-07-14 11:00:00 [INFO] 文字起こしを開始します: recordings/meeting.mp3 (12.3MB)
2026-07-14 11:00:45 [INFO] 文字起こしが完了しました(4521 文字)
2026-07-14 11:00:45 [INFO] ===== ステップ2/3: 議事録の生成 =====
2026-07-14 11:01:10 [INFO] 議事録の生成が完了しました(1032 文字)
2026-07-14 11:01:10 [INFO] ===== ステップ3/3: Google ドキュメントへ保存 =====
2026-07-14 11:01:15 [INFO] すべての処理が完了しました!
2026-07-14 11:01:15 [INFO] 議事録のURL: https://docs.google.com/document/d/xxxx/edit
```

## 生成される議事録の形式

- 【会議概要】
- 【主な議題と議論内容】
- 【決定事項】
- 【TODO・アクションアイテム】
- 【次回への持ち越し事項】

## 注意事項

- Whisper API のファイルサイズ上限は **25MB** です。超える場合は音声を分割するか、ビットレートを下げてください
- `.env`・`credentials.json`・`token.json` は秘密情報のため **絶対に Git にコミットしないでください**(`.gitignore` で除外済み)
- OpenAI API の利用には料金が発生します(Whisper: 約 $0.006/分、gpt-4o-mini: 少額)

## トラブルシューティング

| エラー | 対処法 |
|---|---|
| `OPENAI_API_KEY が設定されていません` | `.env` に APIキーを記述する |
| `Google の認証情報ファイルが見つかりません` | `credentials.json` をプロジェクト直下に置く |
| `トークンのリフレッシュに失敗しました` | `token.json` を削除して再実行(再認証)する |
| `ファイルサイズが上限(25MB)を超えています` | 音声を分割するか低ビットレートで再変換する |
