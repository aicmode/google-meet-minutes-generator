"""
google_docs.py
Google Docs API / Google Drive API を使って、
議事録用のドキュメントを作成・書き込み・フォルダ移動するモジュール。
"""

import logging
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config

logger = logging.getLogger(__name__)


def get_credentials() -> Credentials:
    """
    Google API の認証情報を取得する。

    ・token.json があればそれを再利用する
    ・トークンが期限切れならリフレッシュする
    ・どちらも無ければブラウザを開いて初回認証を行い、token.json に保存する

    Returns:
        Google API の認証情報

    Raises:
        RuntimeError: 認証に失敗した場合
    """
    creds = None

    if not os.path.exists(config.GOOGLE_TOKEN_FILE) and not os.path.isfile(
        config.GOOGLE_CREDENTIALS_FILE
    ):
        raise RuntimeError(
            f"Google OAuth の認証情報ファイルがありません: "
            f"{config.GOOGLE_CREDENTIALS_FILE}。Google Cloud Console から"
            "デスクトップアプリ用の OAuth クライアント JSON をダウンロードし、"
            "この場所へ配置してから再実行してください。"
        )

    # 保存済みのトークンがあれば読み込む
    if os.path.exists(config.GOOGLE_TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(
                config.GOOGLE_TOKEN_FILE, config.GOOGLE_SCOPES
            )
        except (OSError, ValueError) as error:
            raise RuntimeError(
                f"{config.GOOGLE_TOKEN_FILE} を読み込めません。ファイルを削除して"
                "再実行し、Google 認証をやり直してください。"
            ) from error

    # トークンが無効な場合の処理
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # 期限切れのトークンをリフレッシュする
            logger.info("Google のトークンをリフレッシュします")
            try:
                creds.refresh(Request())
            except Exception as error:
                raise RuntimeError(
                    f"トークンのリフレッシュに失敗しました。"
                    f"{config.GOOGLE_TOKEN_FILE} を削除して再認証してください: {error}"
                ) from error
        else:
            # 初回認証:ブラウザを開いて Google アカウントでログインする
            logger.info("ブラウザで Google アカウントの認証を行ってください")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.GOOGLE_CREDENTIALS_FILE, config.GOOGLE_SCOPES
                )
                creds = flow.run_local_server(port=0)
            except Exception as error:
                raise RuntimeError(f"Google の認証に失敗しました: {error}") from error

        # 次回以降のためにトークンを保存する
        with open(config.GOOGLE_TOKEN_FILE, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())
        logger.info("トークンを %s に保存しました", config.GOOGLE_TOKEN_FILE)

    return creds


def create_document(creds: Credentials, title: str) -> str:
    """
    指定したタイトルで新しい Google ドキュメントを作成する。

    Args:
        creds: Google API の認証情報
        title: ドキュメントのタイトル

    Returns:
        作成したドキュメントのID

    Raises:
        RuntimeError: ドキュメントの作成に失敗した場合
    """
    logger.info("Google ドキュメントを作成します: %s", title)

    try:
        docs_service = build("docs", "v1", credentials=creds)
        document = docs_service.documents().create(body={"title": title}).execute()
    except HttpError as error:
        raise RuntimeError(f"Google ドキュメントの作成に失敗しました: {error}") from error

    document_id = document.get("documentId")
    logger.info("ドキュメントを作成しました(ID: %s)", document_id)
    return document_id


def write_minutes(creds: Credentials, document_id: str, minutes: str) -> None:
    """
    作成済みのドキュメントに議事録テキストを書き込む。

    Args:
        creds: Google API の認証情報
        document_id: 書き込み先のドキュメントID
        minutes: 議事録のテキスト

    Raises:
        RuntimeError: 書き込みに失敗した場合
    """
    logger.info("ドキュメントへ議事録を書き込みます")

    # ドキュメントの先頭(index=1)にテキストを挿入するリクエスト
    requests = [
        {
            "insertText": {
                "location": {"index": 1},
                "text": minutes,
            }
        }
    ]

    try:
        docs_service = build("docs", "v1", credentials=creds)
        docs_service.documents().batchUpdate(
            documentId=document_id, body={"requests": requests}
        ).execute()
    except HttpError as error:
        raise RuntimeError(f"ドキュメントへの書き込みに失敗しました: {error}") from error

    logger.info("議事録の書き込みが完了しました")


def move_to_folder(creds: Credentials, document_id: str, folder_id: str) -> None:
    """
    Google Drive API を使って、ドキュメントを指定フォルダへ移動する。

    Args:
        creds: Google API の認証情報
        document_id: 移動するドキュメントのID
        folder_id: 移動先フォルダのID

    Raises:
        RuntimeError: 移動に失敗した場合
    """
    logger.info("ドキュメントをフォルダへ移動します(フォルダID: %s)", folder_id)

    try:
        drive_service = build("drive", "v3", credentials=creds)

        # 現在の親フォルダを取得してから、新しいフォルダへ付け替える
        file = drive_service.files().get(
            fileId=document_id, fields="parents"
        ).execute()
        previous_parents = ",".join(file.get("parents", []))

        drive_service.files().update(
            fileId=document_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields="id, parents",
        ).execute()
    except HttpError as error:
        raise RuntimeError(f"フォルダへの移動に失敗しました: {error}") from error

    logger.info("フォルダへの移動が完了しました")


def save_minutes_to_docs(title: str, minutes: str) -> str:
    """
    議事録を Google ドキュメントとして保存する一連の処理をまとめた関数。

    1. Google API の認証
    2. ドキュメントの新規作成
    3. 議事録の書き込み
    4. (設定されていれば)指定フォルダへ移動

    Args:
        title: ドキュメントのタイトル
        minutes: 議事録のテキスト

    Returns:
        作成したドキュメントのURL
    """
    creds = get_credentials()

    document_id = create_document(creds, title)
    write_minutes(creds, document_id, minutes)

    # .env で保存先フォルダが指定されている場合のみ移動する
    if config.GOOGLE_DRIVE_FOLDER_ID:
        move_to_folder(creds, document_id, config.GOOGLE_DRIVE_FOLDER_ID)

    document_url = f"https://docs.google.com/document/d/{document_id}/edit"
    return document_url
