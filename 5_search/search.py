import argparse
import os
import re
from collections import Counter
from pathlib import Path

import math
import nltk
from pymorphy2 import MorphAnalyzer


class SearchEngine:
    def __init__(self, html_index_path: str, lemmas_tfidf_path: str, inverted_index_path: str):
        self._inverted_index = {}
        self._document_vectors = {}
        self._lemmas_idf = {}
        self._document_norms = {}
        self._html_index = {}

        self._russian_stopwords = self._load_stopwords()
        self._russian_re = re.compile(r'\b[а-яА-ЯёЁ]+\b', re.UNICODE)
        self._load_searh_data(html_index_path, lemmas_tfidf_path, inverted_index_path)


    def _check_that_path_exists(self, path: str):
        if not os.path.exists(path):
            raise ValueError(f"Path {path} does not exist")

    def _check_that_files_by_path_exist(self, path: str):
        self._check_that_path_exists(path)

        if not os.listdir(path):
            raise ValueError(f"Path {path} does not contain files")

    def _load_searh_data(self, html_index_path: str, lemmas_tfidf_path: str, inverted_index_path: str):
        self._check_that_files_by_path_exist(lemmas_tfidf_path)
        self._check_that_path_exists(inverted_index_path)
        self._check_that_path_exists(html_index_path)

        with open(html_index_path, 'r', encoding='utf-8') as f:
            for line in f:
                splitted = line.strip().split("\t")
                self._html_index[splitted[0]] = splitted[1]

        with open(inverted_index_path, 'r', encoding='utf-8') as f:
            for line in f:
                splitted = line.strip().split()
                self._inverted_index[splitted[0]] = set(map(lambda x: x.zfill(4), splitted[1:]))

        for file in os.listdir(lemmas_tfidf_path):
            document_id = Path(file).stem
            vector = {}
            path = os.path.join(lemmas_tfidf_path, file)
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    lemma, idf, tfidf = line.strip().split()
                    idf = float(idf)
                    tfidf = float(idf)

                    vector[lemma] = tfidf
                    self._lemmas_idf[lemma] = idf
            self._document_vectors[document_id] = vector

        for document_id, vector in self._document_vectors.items():
            norm = sum(x * x for x in vector.values())
            self._document_norms[document_id] = math.sqrt(norm)

    def _load_stopwords(self) -> set[str]:
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', quiet=True)

        from nltk.corpus import stopwords
        return set(stopwords.words('russian'))

    def _get_lemma_by_token(self, token: str) -> str:
        return MorphAnalyzer().parse(token)[0].normal_form

    def _get_query_tokens(self, query: str) -> list[str]:
        all_tokens = [token.lower() for token in self._russian_re.findall(query)]
        return list(filter(lambda x: x not in self._russian_stopwords, all_tokens))

    def _get_query_vector(self, lemmas: list[str]) -> tuple[dict[str, float], float]:
        total = len(lemmas)
        lemmas_counter = Counter(lemmas)
        query_vector = {}
        norm = 0.0
        for lemma in lemmas:
            count = lemmas_counter[lemma]
            tf = count / total
            idf = 0.0

            if lemma in self._lemmas_idf:
                idf = self._lemmas_idf.get(lemma, 0.0)
            tfidf = tf * idf
            query_vector[lemma] = tfidf
            norm += tfidf * tfidf
        return query_vector, math.sqrt(norm)

    def _get_document_ids_and_similarity(self, lemmas: list[str]) -> dict[int, float]:
        query_vector, query_norm = self._get_query_vector(lemmas)
        if query_norm == 0.0:
            return {}

        document_ids = set()
        for lemma in lemmas:
            document_ids |= self._inverted_index.get(lemma, set())
        if not document_ids:
            return {}

        similarities = {}
        for document_id in document_ids:
            document_vector = self._document_vectors.get(document_id)
            if document_vector is None:
                continue

            document_norm = self._document_norms.get(document_id, 0.0)
            if document_norm == 0.0:
                continue

            result = 0.0
            for lemma, lemma_tfidf in query_vector.items():
                document_lemma_tfidf = document_vector.get(lemma, 0.0)
                result += lemma_tfidf * document_lemma_tfidf
            similarity = result / (query_norm * document_norm)
            if similarity > 0:
                similarities[document_id] = similarity

        return similarities

    def process_search_query(self, search_query: str) -> list[tuple[str, float]]:
        tokens = self._get_query_tokens(search_query)
        lemmas = list(map(self._get_lemma_by_token, tokens))
        if not lemmas:
            return []

        similarities = self._get_document_ids_and_similarity(lemmas)
        similarities_list = list(map(lambda x: (self._html_index[x], similarities[x]), similarities))
        similarities_list.sort(key=lambda x: x[1], reverse=True)

        return similarities_list


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--html-index-path",
        required=True,
        help="Directory containing html files"
    )
    p.add_argument(
        "--lemmas-tfidf-path",
        required=True,
        help="Directory containing lemmas tfidf files"
    )
    p.add_argument(
        "--index-path",
        required=True,
        help="Path to inverted index"
    )
    args = p.parse_args()

    search_engine = SearchEngine(args.html_index_path, args.lemmas_tfidf_path, args.index_path)
    print("Search engine is ready")

    while True:
        search_query = input("Введите запрос: ").strip()
        if not search_query:
            break

        documents = search_engine.process_search_query(search_query)
        documents_size = len(documents)
        if documents_size == 0:
            print("Документов не найдено")
            continue

        print(f"Найдено {documents_size} документов")
        for i in range(min(documents_size, 10)):
            document_url, similarity = documents[i]
            print(f"{i + 1}: {document_url}. Схожесть - {similarity}")

        if documents_size > 10:
            print(f"И еще {documents_size - 10} документов")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nABORTED")