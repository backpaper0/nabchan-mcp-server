from whoosh.analysis import (
    Tokenizer as WhooshTokenizer,
    Token,
    Analyzer as WhooshAnalyzer,
)
from janome.tokenizer import Tokenizer as JanomeTokenizer
from whoosh.fields import Schema, TEXT, ID


class JapaneseTokenizer(WhooshTokenizer):
    def __init__(self) -> None:
        self.tokenizer = JanomeTokenizer()

    def __call__(self, value, **kwargs):
        assert isinstance(value, str)
        base_pos = 0
        for token in self.tokenizer.tokenize(value):
            tok = Token()
            tok.text = token.surface
            tok.pos = base_pos  # 必須: 文字列内の位置（オフセット）を記録
            tok.boost = 1.0
            tok.startchar = base_pos
            tok.endchar = base_pos + len(token.surface)
            tok.posinc = 1  # 増分（通常は1）
            tok.stopped = False
            tok.stem = ""
            tok.pos_tag = token.part_of_speech  # ← 品詞タグ（任意だけど有用）

            yield tok
            base_pos += len(token.surface)

    def __getstate__(self) -> dict:
        # tokenizerを除外してシリアライズ
        return {}

    def __setstate__(self, state) -> None:
        # 読み込み時にtokenizerを再生成
        self.tokenizer = JanomeTokenizer()


class JapaneseAnalyzer(WhooshAnalyzer):
    def __init__(self):
        self.tokenizer = JapaneseTokenizer()

    def __call__(self, value, **kwargs):
        return self.tokenizer(value, **kwargs)


schema = Schema(
    url=ID(stored=True, unique=True),
    title=TEXT(stored=True),
    description=TEXT(stored=True),
    content=TEXT(analyzer=JapaneseAnalyzer()),
    markdown=TEXT(stored=True, analyzer=None),
)
