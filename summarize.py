"""
summarize.py
文字起こしテキストから OpenAI API(ChatGPT)で議事録を生成するモジュール。
"""

import logging

from openai import OpenAI, OpenAIError

import config

logger = logging.getLogger(__name__)

# AI に渡す役割の指示(システムプロンプト)
SYSTEM_PROMPT = """\
あなたは優秀な議事録作成アシスタントです。
会議の文字起こしテキストを読み、日本語で分かりやすい議事録を作成してください。

以下の形式で出力してください(該当する内容がない項目は「特になし」と記載):

【会議概要】
会議全体の内容を2〜3文で要約する

【主な議題と議論内容】
・議題ごとに議論の内容を箇条書きでまとめる

【決定事項】
・会議で決まったことを箇条書きで列挙する

【TODO・アクションアイテム】
・誰が・何を・いつまでに行うかを箇条書きで列挙する

【次回への持ち越し事項】
・結論が出ず次回に持ち越された内容を列挙する
"""


def generate_minutes(transcript: str) -> str:
    """
    文字起こしテキストを AI に渡して議事録を生成する。

    Args:
        transcript: 文字起こし結果のテキスト

    Returns:
        生成された議事録のテキスト

    Raises:
        ValueError: 文字起こしテキストが空の場合
        RuntimeError: API呼び出しに失敗した場合
    """
    if not transcript or not transcript.strip():
        raise ValueError("文字起こしテキストが空のため、議事録を生成できません。")

    logger.info("議事録の生成を開始します(モデル: %s)", config.OPENAI_MODEL)

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"以下は会議の文字起こしです。議事録を作成してください。\n\n{transcript}",
                },
            ],
            temperature=0.3,  # 議事録なので創造性を抑えて正確さを優先する
        )
    except OpenAIError as error:
        raise RuntimeError(f"OpenAI API での議事録生成に失敗しました: {error}") from error

    minutes = (response.choices[0].message.content or "").strip()

    if not minutes:
        raise RuntimeError("議事録の生成結果が空でした。再度実行してください。")

    logger.info("議事録の生成が完了しました(%d 文字)", len(minutes))
    return minutes
