import re
import random
import os
import streamlit as st
import streamlit.components.v1 as components
from ocr import OCRReader
from ollama import chat  # pdf_input2.py のOllama連携を復活

# キャッシュファイルの保存先
CACHE_FILE = "ocr_cache.txt"
SUMMARY_CACHE_FILE = "summary_cache.txt"  # 要約結果もキャッシュして爆速化

# 1. Streamlit 画面基本設定
st.set_page_config(
    page_title="クトゥルフ神話TRPG専用 AI『何でも屋』LIVE HUD",
    page_icon="🧙‍♂️",
    layout="wide"
)

# セッション状態（常時保存）の初期化
if "ocr_result" not in st.session_state:
    st.session_state.ocr_result = ""
if "summary_result" not in st.session_state:
    st.session_state.summary_result = ""
if "generation_seed" not in st.session_state:
    st.session_state.generation_seed = 0

# アプリ起動時にキャッシュがあれば自動復元（何度も読み込ませる手間を削減）
if not st.session_state.ocr_result and os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        st.session_state.ocr_result = f.read()
if not st.session_state.summary_result and os.path.exists(SUMMARY_CACHE_FILE):
    with open(SUMMARY_CACHE_FILE, "r", encoding="utf-8") as f:
        st.session_state.summary_result = f.read()

st.title("🧙‍♂️ TRPG AI『何でも屋』パレット × 高精度OCR統合システム")
st.write("ルールブック(PDF)の解析から、リアルタイムなセッション支援までを1画面で完結させます。")

# 左右の2カラムに分割
col1, col2 = st.columns([1, 2])

# 2. pdf_input2.py から継承した AIプロンプト ＆ Ollama要約ロジック
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

# 3. 左側：PDF読み込み ＆ 高精度OCR ＆ Ollama要約（pdf_input2.pyの完全合体）
with col1:
    st.header("ルールブックのスキャン ＆ AI要約")
    
    if st.session_state.ocr_result:
        st.success("前回解析したルールブックのデータを自動復元しました！")
        
        if st.button("キャッシュを削除して新しいPDFを読み込む"):
            if os.path.exists(CACHE_FILE): os.remove(CACHE_FILE)
            if os.path.exists(SUMMARY_CACHE_FILE): os.remove(SUMMARY_CACHE_FILE)
            st.session_state.ocr_result = ""
            st.session_state.summary_result = ""
            st.rerun()
            
        # 【復活】Ollamaによるルール要約の表示エリア
        if st.session_state.summary_result:
            st.markdown("### ローカルLLM（Gemma 3）によるルール要約")
            st.markdown(st.session_state.summary_result)
        else:
            if st.button("🔮 ローカルLLMでルールを要約する", type="primary"):
                with st.spinner("Ollama (Gemma 3) がルールを初心者向けに要約中..."):
                    summary = summarize_rule(st.session_state.ocr_result)
                    st.session_state.summary_result = summary
                    with open(SUMMARY_CACHE_FILE, "w", encoding="utf-8") as f:
                        f.write(summary)
                st.rerun()
                
        with st.expander("抽出された生のテキストを確認"):
            st.text_area("OCRテキスト", st.session_state.ocr_result, height=200)
            
    else:
        uploaded_file = st.file_uploader("クトゥルフ神話TRPGルール(PDF)を選択してください", type=["pdf"])
        
        if uploaded_file is not None:
            filename = uploaded_file.name.lower()
            if st.button("🔮 高精度OCRを実行", type="primary"):
                with st.spinner("AIが画像認識(OCR)でルールを解析中..."):
                    reader = OCRReader()
                    if "coc" in filename or "cthulhu" in filename:
                        st.info("CoCルールブックを検出。4〜20ページを限定スキャンします。")
                        result_text = reader.coc_manual(uploaded_file)
                    else:
                        st.info("ルールブック全体をスキャンします。")
                        result_text = reader.pokemon_manual(uploaded_file)
                        
                    st.session_state.ocr_result = result_text
                    with open(CACHE_FILE, "w", encoding="utf-8") as f:
                        f.write(result_text)
                    st.success("スキャン完了！")
                    st.rerun()

# 4. 右側：近未来的 HUD 画面 (nandemo_v.html) の表示 ＆ 変数連携
with col2:
    st.header("LIVE HUD パレット")
    
    if st.button("🔄 状況を更新して別の行動を演算"):
        st.session_state.generation_seed = random.randint(1, 100000)
        st.toast("別の可能性をシミュレーション中...", icon="⚡")

    try:
        with open("nandemo_v.html", "r", encoding="utf-8") as f:
            html_content = f.read()
            
        # HTMLの最上部に、安全にデータを隠すための隠しボックス（div）を注入する
        if st.session_state.ocr_result:
            # 要約結果があれば要約を、なければ生テキストを優先してHUD側に同期させる
            sync_text = st.session_state.summary_result if st.session_state.summary_result else st.session_state.ocr_result
            safe_text = sync_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", " ")
            
            data_bridge = f'<div id="python-ocr-bridge" data-text="{safe_text}" style="display:none;"></div>'
            html_content = data_bridge + html_content
            
            # ドロップエリア（アップローダー部分）を非表示にする
            html_content = html_content.replace(
                "background: #091022; border: 2px dashed #1e293b;",
                "display: none; background: #091022; border: 2px dashed #1e293b;"
            )
            # メイン画面を最初から表示する
            html_content = html_content.replace("display: none;", "display: block;")

        components.html(html_content, height=950, scrolling=True)
        
    except FileNotFoundError:
        st.error("`nandemo_v.html` が見つかりません。")