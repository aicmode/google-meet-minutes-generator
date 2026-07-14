"""
config.py
環境変数(.env)の読み込みと、プロジェクト全体で使う設定値の管理を行うモジュール。

APIキーなどの秘密情報はコードに直接書かず、.env ファイルから読み込む。
"""

import os

from dotenv import load_dotenv

# .env ファイルを読み込んで環境変数に反映する
load_dotenv()

# ----------------------------------------------------------------------------
# OpenAI 関連の設定
# ----------------------------------------------------------------------------

# OpenAI の APIキー(必須)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 文字起こしに使う Whisper のモデル名
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")

# 議事録の生成に使う ChatGPT のモデル名
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ----------------------------------------------------------------------------
# Google API 関連の設定
# ----------------------------------------------------------------------------

# OAuth クライアントの認証情報ファイル(Google Cloud Console からダウンロードする)
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

# 初回認証後に発行されるトークンの保存先ファイル
GOOGLE_TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "token.json")

# 議事録ドキュメントを保存する Google Drive のフォルダID(省略可)
# 空の場合はマイドライブ直下に作成される
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

# Google API のアクセス権限(スコープ)
# ・documents : Google ドキュメントの作成・編集
# ・drive.file : このアプリで作成したファイルの操作(フォルダ移動に使用)
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

# ----------------------------------------------------------------------------
# ファイル・フォルダの設定
# ----------------------------------------------------------------------------

# 録音ファイルを置くフォルダ
RECORDINGS_DIR = os.getenv("RECORDINGS_DIR", "recordings")

# 対応する音声ファイルの拡張子
SUPPORTED_AUDIO_EXTENSIONS = (
    ".mp3",
    ".mp4",
    ".m4a",
    ".wav",
    ".webm",
    ".mpga",
    ".mpeg",
    ".aiff",
    ".aif",
)

# Whisper API が直接受け付けない形式(送信前に WAV へ自動変換する)
CONVERT_TO_WAV_EXTENSIONS = (".aiff", ".aif")

# Whisper API にアップロードできるファイルサイズの上限(25MB)
MAX_AUDIO_FILE_SIZE = 25 * 1024 * 1024


def validate_config() -> None:
    """
    必須の設定値が揃っているかを確認する。

    不足している場合は ValueError を投げて、
    実行前に設定ミスへ気付けるようにする。
    """
    api_key = (OPENAI_API_KEY or "").strip()
    placeholder_values = {"sk-your-api-key-here", "your-api-key-here"}
    if not api_key or api_key.lower() in placeholder_values:
        raise ValueError(
            "OpenAI APIキーが未設定です。プロジェクト直下の .env を開き、"
            "OPENAI_API_KEY=発行したAPIキー の形式で設定してください。"
            "（.env.example の例示値は使用できません）"
        )

    if not os.path.exists(GOOGLE_CREDENTIALS_FILE) and not os.path.exists(
        GOOGLE_TOKEN_FILE
    ):
        raise ValueError(
            f"Google 認証情報が見つかりません: {GOOGLE_CREDENTIALS_FILE}。"
            "Google Cloud Console で『デスクトップアプリ』の OAuth クライアントIDを作成し、"
            f"ダウンロードしたJSONを {GOOGLE_CREDENTIALS_FILE} として配置してください。"
            "詳しい手順は README.md の『Google API の設定』を参照してください。"
        )
