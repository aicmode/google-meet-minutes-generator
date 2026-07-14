"""
main.py
Google Meet の録音ファイルから議事録を自動生成し、
Google ドキュメントへ保存するメインスクリプト。

処理の流れ:
    1. 録音ファイルを読み込む
    2. Whisper API で文字起こし
    3. OpenAI API で議事録を生成
    4. Google Docs API でドキュメントを作成して書き込む

使い方:
    python main.py recordings/meeting.mp3
    python main.py                     # recordings/ 内の最新ファイルを自動選択
"""

import argparse
import logging
import os
import sys
from datetime import datetime

import config
from google_docs import save_minutes_to_docs
from summarize import generate_minutes
from transcribe import transcribe_audio

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """実行ログの出力形式を設定する。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Google API ライブラリの細かいログは抑制する
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)


def find_latest_recording() -> str:
    """
    recordings フォルダから最も新しい音声ファイルを探す。

    Returns:
        最新の音声ファイルのパス

    Raises:
        FileNotFoundError: フォルダや音声ファイルが見つからない場合
    """
    recordings_dir = config.RECORDINGS_DIR

    if not os.path.isdir(recordings_dir):
        raise FileNotFoundError(
            f"録音フォルダが見つかりません: {recordings_dir}"
        )

    # 対応形式の音声ファイルだけを集める
    audio_files = [
        os.path.join(recordings_dir, name)
        for name in os.listdir(recordings_dir)
        if name.lower().endswith(config.SUPPORTED_AUDIO_EXTENSIONS)
    ]

    if not audio_files:
        raise FileNotFoundError(
            f"{recordings_dir} に音声ファイルがありません。"
            "Google Meet の録音ファイルを配置してください。"
        )

    # 更新日時が最も新しいファイルを返す
    latest_file = max(audio_files, key=os.path.getmtime)
    logger.info("最新の録音ファイルを選択しました: %s", latest_file)
    return latest_file


def build_document_title(audio_path: str) -> str:
    """
    録音ファイル名と日時からドキュメントのタイトルを作る。

    Args:
        audio_path: 音声ファイルのパス

    Returns:
        ドキュメントのタイトル(例: 議事録_meeting_2026-07-14)
    """
    file_name = os.path.splitext(os.path.basename(audio_path))[0]
    date_str = datetime.now().strftime("%Y-%m-%d")
    return f"議事録_{file_name}_{date_str}"


def run(audio_path: str) -> str:
    """
    議事録生成の一連の処理を実行する。

    Args:
        audio_path: 録音ファイルのパス

    Returns:
        作成した Google ドキュメントのURL
    """
    # ステップ1: 文字起こし
    logger.info("===== ステップ1/3: 文字起こし =====")
    transcript = transcribe_audio(audio_path)

    # ステップ2: 議事録の生成
    logger.info("===== ステップ2/3: 議事録の生成 =====")
    minutes = generate_minutes(transcript)

    # ステップ3: Google ドキュメントへ保存
    logger.info("===== ステップ3/3: Google ドキュメントへ保存 =====")
    title = build_document_title(audio_path)
    document_url = save_minutes_to_docs(title, minutes)

    return document_url


def main() -> int:
    """
    コマンドライン引数を受け取り、議事録生成を実行するエントリーポイント。

    Returns:
        終了コード(0: 成功, 1: 失敗)
    """
    setup_logging()

    # コマンドライン引数の定義
    parser = argparse.ArgumentParser(
        description="Google Meet の録音から議事録を生成して Google ドキュメントへ保存します"
    )
    parser.add_argument(
        "audio_file",
        nargs="?",
        default=None,
        help="録音ファイルのパス(省略時は recordings/ 内の最新ファイルを使用)",
    )
    args = parser.parse_args()

    try:
        # 設定値(APIキーなど)のチェック
        config.validate_config()

        # 録音ファイルの決定(引数が無ければ最新ファイルを自動選択)
        audio_path = args.audio_file or find_latest_recording()

        # 議事録生成の実行
        document_url = run(audio_path)

        logger.info("すべての処理が完了しました!")
        logger.info("議事録のURL: %s", document_url)
        return 0

    except (FileNotFoundError, ValueError) as error:
        # 設定ミスやファイル不足など、ユーザーが対処できるエラー
        logger.error("エラー: %s", error)
        return 1
    except RuntimeError as error:
        # API呼び出しの失敗など、実行時のエラー
        logger.error("実行時エラー: %s", error)
        return 1
    except KeyboardInterrupt:
        logger.warning("ユーザーによって処理が中断されました")
        return 1
    except Exception:
        # 想定外のエラーはスタックトレース付きで表示する
        logger.exception("想定外のエラーが発生しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
