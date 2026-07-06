import sys
import subprocess

# 【最重要】Streamlitが動いている環境ピンポイントにpypdfを強制インストール
try:
    from pypdf import PdfReader
except ModuleNotFoundError:
    # ターミナルの環境ズレを無視して強制的にインストールを実行
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf"])
    from pypdf import PdfReader

import streamlit as st

# ページの設定
st.set_page_config(page_title="PDF抽出テスト", layout="wide")

st.title("📂 PDFテキスト抽出・集中検証システム")
st.caption("まずはPDFから本物のテキストが正常に剥ぎ取れるかを100%確認します。")

# --- 1. バックエンド：PDFからテキストを抽出する関数 ---
def extract_text_from_pdf(uploaded_file):
    try:
        reader = PdfReader(uploaded_file)
        full_text = ""
        
        # 進行状況を出すためのプログレスバー
        progress_bar = st.progress(0)
        total_pages = len(reader.pages)
        
        for index, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                full_text += f"\n--- --- PAGE {index + 1} --- ---\n" + text + "\n"
            
            # 進行状況を更新
            progress = int((index + 1) / total_pages * 100)
            progress_bar.progress(progress)
            
        return full_text, total_pages
    except Exception as e:
        st.error(f"PDFの解析中にエラーが発生しました: {e}")
        return None, 0

# --- 2. フロントエンド：PDFインプットUI ---
st.markdown("### 1. 本物の「ポケカルール.pdf」をアップロード")
uploaded_file = st.file_uploader("ここにPDFファイルをドラッグ＆ドロップしてください", type=["pdf"])

# --- 3. 抽出結果の表示 ---
if uploaded_file is not None:
    st.success(f"ファイル「{uploaded_file.name}」を受信しました。解析を開始します。")
    
    # テキスト抽出の実行
    with st.spinner("⚡ 現在、PDFの全ページから文字データをスキャン中..."):
        raw_text, page_count = extract_text_from_pdf(uploaded_file)
    
    if raw_text:
        st.balloons() # 成功したらバルーンでお祝い
        st.markdown(f"### 🎉 抽出成功！ (全 {page_count} ページ)")
        st.info("以下に表示されているのが、システムがPDFから直接読み取った**本物の正確なルールデータ**です。")
        
        # スクロール可能なテキストエリアに、抽出された全文字を出力
        st.text_area(
            label="PDFから抽出された生のテキストデータ（全文）", 
            value=raw_text, 
            height=500
        )
        
        # 審査員アピール用に、文字数などの統計も表示
        st.markdown("#### 📊 データ統計")
        col1, col2 = st.columns(2)
        col1.metric("総文字数", f"{len(raw_text)} 文字")
        col2.metric("総ページ数", f"{page_count} ページ")
else:
    st.info("💡 使い方：上のエリアにPDFを入れると、即座にPythonが文字を解析してここに展開します。")