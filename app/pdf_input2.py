import re
import streamlit as st
import fitz
from ollama import chat

# ==============================
# Streamlit設定
# ==============================

st.set_page_config(
    page_title="ゲームルール要約システム",
    page_icon=":video_game:",
    layout="wide"
)

st.title(":video_game: ゲームルール要約システム")
st.write("ルールブック(PDF)からゲームの基本情報を抽出します。")

uploaded_file = st.file_uploader(
    "ルールブック(PDF)を選択してください",
    type=["pdf"]
)

# ==============================
# PDF読込（PyMuPDF）
# ==============================

def extract_text(uploaded_file, start_page=1, end_page=None):

    pdf = fitz.open(
        stream=uploaded_file.read(),
        filetype="pdf"
    )

    if end_page is None:
        end_page = len(pdf)

    text = ""

    progress = st.progress(0)

    total = end_page - start_page + 1

    for page_num in range(start_page - 1, end_page):

        page = pdf.load_page(page_num)

        page_text = page.get_text("text")

        if page_text:
            text += page_text + "\n"

        progress.progress((page_num - start_page + 2) / total)

    progress.empty()

    pdf.close()

    return text





# ==============================
# テキスト整形
# ==============================

def clean_text(text):

    text = text.replace("\r", "\n")

    text = re.sub(r"\n+", "\n", text)

    text = re.sub(r"[ \t]+", " ", text)

    text = re.sub(r" +", " ", text)

    return text.strip()





# ==============================
# デバッグ表示
# ==============================

def show_debug(text):

    with st.expander("抽出したテキストを確認"):

        st.write("文字数:", len(text))

        st.text(text[:3000])





# ==============================
# AIへ渡すプロンプト作成
# ==============================

def create_prompt(text):

    prompt = f"""
あなたは日本語専門のゲームルール解説AIです。

以下のルールブックを読み取り、
必ず日本語のみで回答してください。

英語は禁止です。

入力が英語でも日本語へ翻訳してから回答してください。

ゲームのルールを初心者向けに整理してください。

以下の項目を出力してください。

## ゲーム概要

## 勝利条件

## クリア条件

## ゲームの流れ

## 基本行動

## 注意事項

## 初心者へのアドバイス

各項目は箇条書きで、
できるだけ簡潔にまとめてください。

--------------------

ルールブック

{text}
"""

    return prompt
# ==============================
# Ollamaで要約
# ==============================

def summarize_rule(text):

    prompt = create_prompt(text)

    response = chat(
        model="gemma3:4b",
        messages=[
            {
                "role": "system",
                "content": (
                    "あなたは日本語だけで回答するゲームルール解説AIです。"
                    "入力が英語でも日本語でも、必ず日本語で回答してください。"
                    "見出しも本文も日本語で出力してください。"
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]





# ==============================
# メイン処理
# ==============================

if uploaded_file is not None:

    filename = uploaded_file.name.lower()

    try:

        # --------------------------
        # CoCのみ4～20ページ
        # --------------------------
        if "coc" in filename or "cthulhu" in filename:

            st.info("CoCルールブックを検出しました。（4～20ページを解析します）")

            rule_text = extract_text(
                uploaded_file,
                start_page=4,
                end_page=20
            )

        else:

            st.info("ルールブック全体を解析します。")

            rule_text = extract_text(uploaded_file)

        rule_text = clean_text(rule_text)

        st.success("PDFの読み込みが完了しました。")

        st.write("抽出文字数 :", len(rule_text))

        show_debug(rule_text)

        if st.button("ゲーム情報を抽出"):

            if len(rule_text) < 100:

                st.error("PDFから十分な文字を抽出できませんでした。")

            else:

                with st.spinner("AIが解析中です..."):

                    result = summarize_rule(rule_text)

                st.success("解析が完了しました。")

                st.markdown("## :clipboard: 抽出結果")

                st.markdown(result)

    except Exception as e:

        st.error("エラーが発生しました。")

        st.exception(e)





# ==============================
# フッター
# ==============================

st.divider()

st.caption("Hackathon Game Rule Analyzer")