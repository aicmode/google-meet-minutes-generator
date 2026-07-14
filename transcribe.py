"""
transcribe.py
Google Meet の録音ファイルを OpenAI Whisper API で文字起こしするモジュール。
"""

import logging
import os
import subprocess
import tempfile

from openai import OpenAI, OpenAIError

import config

logger = logging.getLogger(__name__)


def validate_audio_file(file_path: str) -> None:
    """
    音声ファイルが文字起こし可能かどうかを事前にチェックする。

    Args:
        file_path: 音声ファイルのパス

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        ValueError: 拡張子が非対応、またはサイズが上限を超えている場合
    """
    # ファイルの存在チェック
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"録音ファイルが見つかりません: {file_path}")

    # 拡張子のチェック
    extension = os.path.splitext(file_path)[1].lower()
    if extension not in config.SUPPORTED_AUDIO_EXTENSIONS:
        raise ValueError(
            f"非対応のファイル形式です: {extension} "
            f"(対応形式: {', '.join(config.SUPPORTED_AUDIO_EXTENSIONS)})"
        )

    # ファイルサイズのチェック(Whisper API の上限は 25MB)
    file_size = os.path.getsize(file_path)
    if file_size > config.MAX_AUDIO_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        raise ValueError(
            f"ファイルサイズが上限(25MB)を超えています: {size_mb:.1f}MB。"
            "音声を分割するか、ビットレートを下げて再変換してください。"
        )


def convert_to_wav(file_path: str) -> str:
    """
    Whisper API が直接受け付けない形式(AIFF など)を一時的な WAV ファイルへ変換する。

    Args:
        file_path: 変換元の音声ファイルのパス

    Returns:
        変換後の一時 WAV ファイルのパス(呼び出し側で削除すること)

    Raises:
        RuntimeError: 変換に失敗した場合
    """
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file.close()

    try:
        # macOS 標準の afconvert で 16bit リトルエンディアンの WAV に変換する
        subprocess.run(
            ["afconvert", "-f", "WAVE", "-d", "LEI16", file_path, temp_file.name],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        os.unlink(temp_file.name)
        raise RuntimeError(
            f"WAV への変換に失敗しました: {file_path} ({error})"
        ) from error

    return temp_file.name


def transcribe_audio(file_path: str) -> str:
    """
    録音ファイルを読み込み、Whisper API で文字起こしを行う。

    Args:
        file_path: 音声ファイルのパス

    Returns:
        文字起こし結果のテキスト

    Raises:
        RuntimeError: API呼び出しに失敗した場合や、結果が空だった場合
    """
    # 事前チェック(存在・形式・サイズ)
    validate_audio_file(file_path)

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    logger.info("文字起こしを開始します: %s (%.1fMB)", file_path, file_size_mb)

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    # Whisper API が直接受け付けない形式は、送信用に WAV へ変換する
    upload_path = file_path
    temp_wav_path = None
    extension = os.path.splitext(file_path)[1].lower()
    if extension in config.CONVERT_TO_WAV_EXTENSIONS:
        logger.info("%s 形式は Whisper API 非対応のため、WAV へ変換します", extension)
        temp_wav_path = convert_to_wav(file_path)
        upload_path = temp_wav_path

    try:
        # 音声ファイルをバイナリモードで開いて Whisper API に送信する
        with open(upload_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model=config.WHISPER_MODEL,
                file=audio_file,
                language="ja",  # 日本語の会議を想定
            )
    except OpenAIError as error:
        raise RuntimeError(f"Whisper API での文字起こしに失敗しました: {error}") from error
    finally:
        # 変換で作った一時ファイルを削除する
        if temp_wav_path is not None:
            os.unlink(temp_wav_path)

    transcript = (response.text or "").strip()

    # 無音ファイルなどで結果が空になるケースへの対処
    if not transcript:
        raise RuntimeError(
            "文字起こし結果が空でした。録音ファイルに音声が含まれているか確認してください。"
        )

    logger.info("文字起こしが完了しました(%d 文字)", len(transcript))
    return transcript
