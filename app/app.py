import os
import streamlit as st
import streamlit.components.v1 as components
from ocr import OCRReader
from ollama import chat  # Ollama連携

# ==============================
# 定数
# ==============================
CACHE_FILE = "ocr_cache.txt"                # OCR結果のキャッシュ
SUMMARY_CACHE_FILE = "summary_cache.txt"    # 要約結果のキャッシュ

# 同梱ルールブックPDFのパス（本番用に固定）
# ※ このファイル名・配置場所は実際に用意するPDFに合わせて変更してください
DEFAULT_PDF_PATH = os.path.join(os.path.dirname(__file__), "rulebook_coc.pdf")

# ==============================
# 1. Streamlit 画面基本設定
# ==============================
st.set_page_config(
    page_title="クトゥルフ神話TRPG専用 AI『何でも屋』LIVE HUD",
    layout="wide"
)

# セッション状態（常時保存）の初期化
if "ocr_result" not in st.session_state:
    st.session_state.ocr_result = ""
if "summary_result" not in st.session_state:
    st.session_state.summary_result = ""

# ==============================
# 起動時の自動読み込みロジック
# ==============================
# OCR結果：キャッシュがあれば復元、なければ同梱PDFを自動解析してキャッシュを作る
if not st.session_state.ocr_result:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            st.session_state.ocr_result = f.read()
    elif os.path.exists(DEFAULT_PDF_PATH):
        with st.spinner("初回起動：ルールブックを解析中です（少し時間がかかります）..."):
            reader = OCRReader()
            result_text = reader.coc_manual(DEFAULT_PDF_PATH)
            st.session_state.ocr_result = result_text
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                f.write(result_text)
    else:
        st.error(
            f"ルールブックPDFが見つかりません（{DEFAULT_PDF_PATH}）。"
            "管理者に連絡し、PDFを配置してもらってください。"
        )

# 要約結果：キャッシュがあれば復元（要約はボタン操作で生成するためここでは自動生成しない）
if not st.session_state.summary_result and os.path.exists(SUMMARY_CACHE_FILE):
    with open(SUMMARY_CACHE_FILE, "r", encoding="utf-8") as f:
        st.session_state.summary_result = f.read()

st.title("TRPG AI『何でも屋』パレット × 高精度OCR統合システム")
st.write("ルールブック(PDF)の解析から、リアルタイムなセッション支援までを1画面で完結させます。")

# 左右の2カラムに分割
col1, col2 = st.columns([1, 2])

# ==============================
# 2. AIプロンプト ＆ Ollama要約ロジック
# ==============================
def create_prompt(text):
    return f"""
あなたは日本語専門のゲームルール解説AIです。
以下のルールブックを読み取り、必ず日本語のみで回答してください。英語は禁止です。
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

各項目は箇条書きで、できるだけ簡潔にまとめてください。
--------------------
ルールブック
{text}
"""

def summarize_rule(text):
    prompt = create_prompt(text)
    response = chat(
        model="gemma3:4b",
        messages=[
            {
                "role": "system",
                "content": "あなたは日本語だけで回答するゲームルール解説AIです。必ず日本語で回答してください。"
            },
            {"role": "user", "content": prompt}
        ]
    )
    return response["message"]["content"]

# ==============================
# 3. 左側：ルール要約表示
# ==============================
with col1:
    st.header("ルールブックの解析結果 ＆ AI要約")

    if st.session_state.ocr_result:
        if st.session_state.summary_result:
            st.markdown("### ローカルLLM（Gemma 3）によるルール要約")
            st.markdown(st.session_state.summary_result)
        else:
            if st.button("ローカルLLMでルールを要約する", type="primary"):
                with st.spinner("Ollama (Gemma 3) がルールを初心者向けに要約中..."):
                    summary = summarize_rule(st.session_state.ocr_result)
                    st.session_state.summary_result = summary
                    with open(SUMMARY_CACHE_FILE, "w", encoding="utf-8") as f:
                        f.write(summary)
                st.rerun()

        with st.expander("抽出された生のテキストを確認"):
            st.text_area("OCRテキスト", st.session_state.ocr_result, height=200)
    else:
        st.warning("ルールブックのデータがまだ準備できていません。")

# ==============================
# 4. 右側：近未来的 HUD 画面 (nandemo_v.html) の表示 ＆ 変数連携
# ==============================
with col2:
    st.header("LIVE HUD パレット")

    try:
        with open("nandemo_v.html", "r", encoding="utf-8") as f:
            html_content = f.read()

        # HTMLの最上部に、安全にデータを隠すための隠しボックス（div）を注入する
        if st.session_state.ocr_result:
            # 要約結果があれば要約を、なければ生テキストを優先してHUD側に同期させる
            sync_text = st.session_state.summary_result if st.session_state.summary_result else st.session_state.ocr_result
            safe_text = (
                sync_text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", " ")
            )

            data_bridge = f'<div id="python-ocr-bridge" data-text="{safe_text}" style="display:none;"></div>'
            html_content = data_bridge + html_content

            # systemMain だけを対象にした安全な置換（他のdisplay:none;を巻き込まない）
            html_content = html_content.replace(
                '<div id="systemMain" style="display: none;">',
                '<div id="systemMain" style="display: block;">'
            )

        components.html(html_content, height=950, scrolling=True)

    except FileNotFoundError:
        st.error("`nandemo_v.html` が見つかりません。")