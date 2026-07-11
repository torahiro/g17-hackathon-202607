import fitz
import easyocr
import numpy as np
from PIL import Image



class OCRReader:

    def __init__(self):
        # 日本語 + 英語対応
        self.reader = easyocr.Reader(
            ['ja', 'en'],
            gpu=False
        )

    def pdf_to_text(self, pdf_source, start_page=1, end_page=None):
        # ファイルパス(str)とアップロードファイルオブジェクトの両方に対応
        if isinstance(pdf_source, str):
            pdf = fitz.open(pdf_source)
        else:
            pdf = fitz.open(stream=pdf_source.read(), filetype="pdf")


        for page_num in range(start_page - 1, end_page):

            page = pdf.load_page(page_num)

            # 画像としてレンダリング（解像度を上げる）
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

            img = Image.frombytes(
                "RGB",
                [pix.width, pix.height],
                pix.samples
            )

            img = np.array(img)

            # OCR実行
            result = self.reader.readtext(
                img,
                detail=0,
                paragraph=True
            )

            page_text = "\n".join(result)

            text += page_text + "\n\n"

        pdf.close()

        return text

    def pokemon_manual(self, pdf_source):

        return self.pdf_to_text(
            pdf_source,
            start_page=1
        )

    def coc_manual(self, pdf_source):
        return self.pdf_to_text(pdf_source, start_page=4, end_page=20)