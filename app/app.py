import re
import fitz  # PyMuPDF
import numpy as np
import streamlit as st
from PIL import Image
from ollama import chat

# EasyOCRのインポート（環境がない場合は警告を出す）
try:
    import easyocr

    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False

# ==============================
# Streamlit 初期設定
# ==============================
st.set_page_config(
    page_title="TRPG & ゲームルール AIアシスタント",
    page_icon=":wizard:",
    layout="wide",
)

st.title(":wizard: TRPG & ゲームルール 統合AIアシスタント")
st.write(
    "ルールブック(PDF)の解析から、セッション中のリアルタイムな行動提案までをサポートします。"
)


# ==============================
# バックエンドロジック (OCR & テキスト抽出)
# ==============================
@st.cache_resource
def load_ocr_reader():
    if HAS_EASYOCR:
        # 日本語と英語に対応
        return easyocr.Reader(["ja", "en"], gpu=False)
    return None


def extract_text_hybrid(uploaded_file, start_page=1, end_page=None, use_ocr=False):
    """デジタルテキスト抽出とOCRを選択・ハイブリッド実行する関数"""
    pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")

    if end_page is None:
        end_page = len(pdf)

    text = ""
    progress = st.progress(0)
    total = end_page - start_page + 1

    reader = load_ocr_reader() if use_ocr else None

    for idx, page_num in enumerate(range(start_page - 1, end_page)):
        page = pdf.load_page(page_num)

        if use_ocr and reader is not None:
            # ocr.py の画像レンダリングロジック
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_array = np.array(img)
            result = reader.readtext(img_array, detail=0, paragraph=True)
            page_text = "\n".join(result)
        else:
            # pdf_input2.py の標準テキスト抽出ロジック
            page_text = page.get_text("text")

        if page_text:
            text += page_text + "\n"

        progress.progress((idx + 1) / total)

    progress.empty()
    pdf.close()
    return text


def clean_text(text):
    text = text.replace("\r", "\n")
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


# ==============================
# AIプロンプト作成 & 送信 (Ollama)
# ==============================
def summarize_rule(text):
    """ルールブックの概要を要約する (モードA)"""
    prompt = f"あなたは日本語専門のゲームルール解説AIです。ゲームのルールを初心者向けに整理してください。\n\n## ゲーム概要\n## 勝利条件\n## クリア条件\n## ゲームの流れ\n## 基本行動\n## 注意事項\n## 初心者へのアドバイス\n\nルールブック:\n{text}"
    response = chat(
        model="gemma3:4b",
        messages=[
            {
                "role": "system",
                "content": "必ず日本語のみで、指定された見出しの箇条書きで出力してください。",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return response["message"]["content"]


def analyze_live_situation(context, rule_text_snippet=""):
    """現在のセッション状況とプレイヤー情報から最適解を提案する (モードB - nandemo_v.htmlの再現)"""
    skills_str = ", ".join([f"{s['name']}({s['val']}%)" for s in context["skills"]])

    system_instruction = """
    あなたはクトゥルフ神話TRPG（第7版）のキーパー（KP）を補助する優秀な『何でも屋AIコンシェルジュ』です。
    ユーザーが入力した【現在の状況文】を分析し、その描写内に登場する具体的なオブジェクト（例：日記、扉、食器棚など）に即座に干渉・対処できる行動提案（王道・技術・奇策の3点）を生成してください。
    
    【絶対厳守のTRPGルール・制約】
    1. プレイヤーは初心者です。特殊なダイス補正はない前提（補正なしベース）で、わかりやすく処理ルールをアドバイスしてください。
    2. 提案の中から「心理学」に関する言及、および心理学技能を使った行動の提案は一切除外してください。
    3. 直前のダイス状態（大成功・成功・失敗・大失敗）を踏まえ、次にとるべきリカバー行動や結果の反映を状況に絡めて提示してください。
    """

    user_prompt = f"""
    【参照ルールブックの断片】
    {rule_text_snippet[:1000]}

    【現在の状況・KPの描写】
    {context['situation']}

    【直前のダイス状態】
    {context['dice_state']}

    【プレイヤーのキャラクター情報】
    役職（職業）: {context['occupation']}
    プレイ人数: {context['player_count']}人
    所持技能リスト: {skills_str}
    
    上記を踏まえ、次の構成で出力してください。
    1. 【複合解析】(現状の初心者向け解説、ダイス結果のハプニングやリカバーの方向性)
    2. 【王道アクション】(基本技能や状況に即したストレートな行動と想定成功率%)
    3. 【技術アクション】(応用・周囲の状況や手分けを活かした行動と想定成功率%)
    4. 【奇策アクション】(職業の特性やひらめきを絡めたトリッキーな行動と想定成功率%)
    """

    response = chat(
        model="gemma3:4b",
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response["message"]["content"]


# ==============================
# メイン画面レイアウト (Streamlit)
# ==============================
uploaded_file = st.file_uploader(
    "ルールブック(PDF)を選択してください", type=["pdf"]
)

if uploaded_file is not None:
    filename = uploaded_file.name.lower()

    # 1. PDF読み込み設定
    st.sidebar.header("📁 PDF抽出設定")
    use_ocr = st.sidebar.checkbox(
        "EasyOCRを使用する (スキャンされたPDFや画像向け)", value=False
    )
    if use_ocr and not HAS_EASYOCR:
        st.sidebar.error("easyocr パッケージがインストールされていません。")

    # クトゥルフ自動判別
    if "coc" in filename or "cthulhu" in filename:
        st.sidebar.info("CoCルールブックを検出: 4～20ページを自動対象にします。")
        start_p = st.sidebar.number_input("開始ページ", value=4)
        end_p = st.sidebar.number_input("終了ページ", value=20)
    else:
        start_p = st.sidebar.number_input("開始ページ", value=1)
        end_p = st.sidebar.number_input("終了ページ", value=None)

    # テキスト抽出実行
    if "rule_text" not in st.session_state:
        with st.spinner("PDFからテキストを抽出中..."):
            raw_text = extract_text_hybrid(
                uploaded_file, start_page=start_p, end_page=end_p, use_ocr=use_ocr
            )
            st.session_state.rule_text = clean_text(raw_text)
        st.success("PDFの読み込みが完了しました！")

    # 2. アプリケーションモードの選択
    app_mode = st.radio(
        "実行する機能を選択してください",
        ["📝 モードA: ルールブック要約", "🧙‍♂️ モードB: クトゥルフ専用 LIVE HUD"],
        horizontal=True,
    )

    st.divider()

    # --------------------------------------------------
    # モードA: ルールブック要約
    # --------------------------------------------------
    if app_mode == "📝 モードA: ルールブック要約":
        st.subheader("📝 ゲームルール要約システム")
        st.write(f"抽出文字数: {len(st.session_state.rule_text)}")

        with st.expander("抽出したテキストの確認"):
            st.text(st.session_state.rule_text[:3000])

        if st.button("ゲーム情報を抽出・要約"):
            if len(st.session_state.rule_text) < 100:
                st.error("十分な文字数を抽出できませんでした。")
            else:
                with st.spinner("AIが解析中..."):
                    summary = summarize_rule(st.session_state.rule_text)
                st.markdown("### :clipboard: 抽出結果")
                st.markdown(summary)

    # --------------------------------------------------
    # モードB: クトゥルフ専用 LIVE HUD (nandemo_v.html の統合)
    # --------------------------------------------------
    elif app_mode == "🧙‍♂️ モードB: クトゥルフ専用 LIVE HUD":
        st.subheader("🧙‍♂️ クトゥルフ神話TRPG専用 AI『何でも屋』LIVE HUD")

        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("### 👤 探索者・セッション設定")
            player_level = st.selectbox(
                "あなたのルール理解度",
                ["🔰 初心者（補正なし想定）", "🏃 中級者", "🔥 上級者"],
            )
            player_count = st.slider("プレイ人数（自分を含む）", 1, 6, 3)
            occupation = st.text_input("あなたの役職（職業）", value="私立探偵")

            st.markdown("---")
            st.markdown("📋 **所持技能値リスト (%)**")
            meboshi_val = st.number_input("目星", 1, 99, 70)
            tosho_val = st.number_input("図書館", 1, 99, 65)

            # 動的技能追加のシミュレート
            extra_skill_name = st.text_input("追加技能名 (任意)", value="")
            extra_skill_val = st.number_input("追加技能値", 1, 99, 50)

        with col2:
            st.markdown("### 🎲 リアルタイム状況入力")
            situation = st.text_area(
                "現在の状況・KPの描写",
                value="古い物置部屋。目の前に、不自然に木の板で頑丈に封鎖された古い食器棚が置かれている。",
                height=100,
            )

            dice_state = st.selectbox(
                "直前のダイス成否",
                [
                    "none: まだ振っていない",
                    "critical: 大成功",
                    "success: 成功",
                    "failed: 失敗",
                    "fumble: 大大失敗",
                ],
            )

            if st.button("⚡ 状況を解析して最適解を生成", type="primary"):
                # プレイヤーコンテキストの組み立て
                skills = [{"name": "目星", "val": meboshi_val}, {"name": "図書館", "val": tosho_val}]
                if extra_skill_name:
                    skills.append({"name": extra_skill_name, "val": extra_skill_val})

                context = {
                    "player_count": player_count,
                    "occupation": occupation,
                    "situation": situation,
                    "dice_state": dice_state.split(":")[0],
                    "skills": skills,
                }

                with st.spinner("AIが戦況とルールをトリギュレーション中..."):
                    analysis_output = analyze_live_situation(
                        context, st.session_state.rule_text
                    )

                st.markdown("### 💡 AIコンシェルジュの提案")
                st.info(analysis_output)

st.divider()
st.caption("Hackathon Game Rule Analyzer Pro - Powered by Streamlit & Ollama")