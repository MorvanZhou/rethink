import re
from pathlib import Path
from typing import List

import jieba.analyse
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

STOP_WORDS_FILE = Path(__file__).parent / "data" / "stop_words.txt"
IDF_FILE = Path(__file__).parent / "data" / "idf.txt"
ENG_IDF_FILE = Path(__file__).parent / "data" / "wiki_idf.txt"


class TFIDF:
    drop_pattern = re.compile(r"[^\u4e00-\u9fa5a-zA-Z0-9 ]")

    def __init__(self):
        self.stop_words, idf, vocabulary = self._load_dict()
        self.vectorizer = TfidfVectorizer(
            tokenizer=self.tokenizer,
            token_pattern=None,
            dtype=np.float32,
        )
        self.vectorizer.idf_ = idf
        self.vectorizer.vocabulary_ = vocabulary

    @staticmethod
    def _load_dict():
        sw = set(STOP_WORDS_FILE.read_text(encoding="utf-8").splitlines())
        lines = IDF_FILE.read_text(encoding="utf-8").splitlines()
        lines.extend(ENG_IDF_FILE.read_text(encoding="utf-8").splitlines())
        vocabulary = {}
        idf = np.empty(len(lines), dtype=np.float32)
        for i, line in enumerate(lines):
            w, f = line.split(" ")
            vocabulary[w] = i
            idf[i] = float(f)
        return sw, idf, vocabulary

    def tokenizer(self, text: str) -> List[str]:
        text = text.lower()
        text = self.drop_pattern.sub("", text)
        for w in jieba.cut_for_search(text):
            if w.strip() == "":
                continue
            if w in self.stop_words:
                continue
            yield w

    def docs2vec(self, docs: List[str]) -> np.ndarray:
        return self.vectorizer.transform(docs)

    def search(self, query: str, docs_vec: np.ndarray, n: int = 5) -> List[int]:
        """
        search top n similar docs

        Args:
            query (str): search text
            docs_vec (np.ndarray): candidate docs in vector
            n (int): return top n similar docs

        Returns:
            List[int]: top n similar docs index
        """
        q_vec = self.vectorizer.transform([query])
        cs = cosine_similarity(docs_vec, q_vec)
        top_n = cs.ravel().argsort()[-n:][::-1]
        return top_n

# tfidf = TFIDF()
