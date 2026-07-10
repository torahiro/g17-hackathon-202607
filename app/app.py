import re
import streamlit as st
import streamlit.components.v1 as components
from ocr import OCRReader  # 作成した ocr.py から読み込み

# Streamlitの基本設定
st.set_page_config(
    page_title="TRPG AI『何でも屋』統合システム",
    page_icon=":🧙‍♂️:",
    layout="wide"
)

# セッション状態の初期化（解析結果を保持するため）
if "ocr_result" not in st.session_state:
    st.session_state.ocr_result = ""

st.title("🧙‍♂️ TRPG AI『何でも屋』パレット × 高精度OCRスキャナー")

# 左右の2カラムに分割（左：PDFアップローダー、右：HTML HUD画面）
col1, col2 = st.columns([1, 2])

with col1:
    st.header("💾 ルールブックのスキャン")
    uploaded_file = st.file_uploader(
        "クトゥルフ神話TRPGルール(PDF)を選択してください",
        type=["pdf"]
    )
    
    if uploaded_file is not None:
        filename = uploaded_file.name.lower()
        
        if st.button("🔮 高精度OCRを実行"):
            with st.spinner("AIが画像認識(OCR)でルールを解析中..."):
                # ocr.py のクラスを呼び出し
                reader = OCRReader()
                
                if "coc" in filename or "cthulhu" in filename:
                    st.info("CoCルールブックを検出。4〜20ページをスキャンします。")
                    result_text = reader.coc_manual(uploaded_file)
                else:
                    st.info("全体をスキャンします。")
                    result_text = reader.pokemon_manual(uploaded_file)
                    
                st.session_state.ocr_result = result_text
                st.success("スキャンが完了しました！")
                
            st.text_area("抽出されたテキスト（デバッグ用）", st.session_state.ocr_result, height=200)

with col2:
    st.header("🎮 LIVE HUD パレット")
    
    # 外部の nandemo_v.html を読み込む
    with open("nandemo_v.html", "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # 【重要】Python側で解析したテキストを、HTMLの初期値（JavaScript）に埋め込む
    # HTML内の特定のテキストを置換するか、JSの変数に代入させます
    if st.session_state.ocr_result:
        # 抽出したテキストをHTML内の初期描写の代わりに流し込む簡易的な仕組み
        escaped_text = st.session_state.ocr_result.replace("'", "\\'").replace("\n", " ")
        html_content = html_content.replace(
            'document.getElementById(\'situationInput\').value = "古い物置部屋。目の前に、不自然に木の板で頑丈に封鎖された古い食器棚が置かれている。";',
            f"document.getElementById('situationInput').value = '{escaped_text[:500]}...（OCRデータ読み込み成功）';"
        )

    # Streamlit上でHTML画面を巨大なインラインフレームとして表示
    components.html(html_content, height=900, scrolling=True)