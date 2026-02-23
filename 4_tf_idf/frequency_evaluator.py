import argparse
import os.path
import re
from collections import Counter
from functools import reduce
from pathlib import Path

import math
from bs4 import BeautifulSoup


class BaseFrequencyEvaluator:
    def extract_text_from_html(self, html_path: str) -> str:
        """
        Извлекает текстовый контент из HTML файла, исключая шапку, footer, скрипты и стили.

        Args:
            html_path: Путь к HTML файлу.

        Returns:
            Извлеченный текст.
        """
        with open(html_path, "r", encoding="windows-1251") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")

        # Удаляем нежелательные элементы
        for element in soup.find_all(["script", "style"]):
            element.decompose()

        # Удаляем шапку и footer по ID
        for element_id in ["hdr", "btmex"]:
            element = soup.find(id=element_id)
            if element:
                element.decompose()

        # Извлекаем основной контент из div с id="text" и class="t hya"
        content_div = soup.find(id="text")
        if content_div:
            text = content_div.get_text(separator=" ", strip=True)
        else:
            # Если div не найден, берем весь текст
            text = soup.get_text(separator=" ", strip=True)

        return text.lower()

    def get_words_frequences(self, text: str) -> Counter:
        words = re.findall(r'\b\w+\b', text.lower())
        return Counter(words)


class TermFrequencyEvaluator(BaseFrequencyEvaluator):
    def __init__(self, htmls_path: str, tokens_path: str, lemmas_path: str):
        self.htmls_path = htmls_path
        self.tokens_path = tokens_path
        self.lemmas_path = lemmas_path
        self.token_file_template = "tokens_{html_id}.txt"
        self.lemma_file_template = "lemmas_{html_id}.txt"

    def get_term_frequencies_for_document(self, document_name: str) -> tuple[dict[str, int], dict[str, int]]:
        pattern = re.compile(r'(\d+)\.html$')
        match = pattern.match(document_name)
        if not match:
            raise ValueError("Invalid html file name's format" + document_name)

        number = match.group(1)
        html_tokens_path = os.path.join(self.tokens_path, self.token_file_template.format(html_id=number))
        with open(html_tokens_path, 'r') as file:
            html_tokens = list(map(lambda x: x.strip(), file.readlines()))

        html_lemmas_path = os.path.join(self.lemmas_path, self.lemma_file_template.format(html_id=number))
        with open(html_lemmas_path, 'r') as file:
            html_lemmas = list(map(lambda x: x.split()[0], file.readlines()))

        document_path = os.path.join(self.htmls_path, document_name)
        text = self.extract_text_from_html(document_path)
        counter = self.get_words_frequences(text)

        token_frequences = {}
        lemma_frequences = {}
        for html_token in html_tokens:
            token_frequences[html_token] = counter[html_token]
        for html_lemma in html_lemmas:
            lemma_frequences[html_lemma] = counter[html_lemma]

        return token_frequences, lemma_frequences


class InverseDocumentFrequencyEvaluator(BaseFrequencyEvaluator):
    def __init__(self, htmls_path: str):
        self.counters = {}
        self.count_of_documents = 0
        for html_file in os.listdir(htmls_path):
            self.count_of_documents += 1
            html_path = os.path.join(htmls_path, html_file)
            text = self.extract_text_from_html(html_path)
            self.counters[html_file] = self.get_words_frequences(text)


    def get_inverse_document_frequency_for_word(self, word: str) -> float:
        df = reduce(lambda x, y: x + min(1, y[word]), self.counters.values(), 0)
        return 0.0 if df == 0 else math.log2(self.count_of_documents / df)

def evaluate_frequences(htmls_path: str, lemmas_path: str, tokens_path: str, output: str):
    path = Path(output)
    path.mkdir(parents=True, exist_ok=True)
    (path / "tokens").mkdir(parents=True, exist_ok=True)
    (path / "lemmas").mkdir(parents=True, exist_ok=True)

    term_frequency_evaluator = TermFrequencyEvaluator(htmls_path, tokens_path, lemmas_path)
    inverse_document_frequency_evaluator = InverseDocumentFrequencyEvaluator(htmls_path)
    for file in os.listdir(htmls_path):
        tokens_tfs, lemmas_tfs = term_frequency_evaluator.get_term_frequencies_for_document(file)
        with (
            open(os.path.join(output, "tokens", file.replace("html", "txt")), 'w') as token_write,
            open(os.path.join(output, "lemmas", file.replace("html", "txt")), 'w') as lemma_write
        ):
            for token, token_tf in tokens_tfs.items():
                token_idf_value = inverse_document_frequency_evaluator.get_inverse_document_frequency_for_word(token)
                token_write.write(f"{token} {token_idf_value} {token_tf * token_idf_value}\n")
            for lemma, lemma_tf in lemmas_tfs.items():
                lemma_idf_value = inverse_document_frequency_evaluator.get_inverse_document_frequency_for_word(lemma)
                lemma_write.write(f"{lemma} {lemma_idf_value} {lemma_tf * lemma_idf_value}\n")
        print("Обработан " + file)


def main():
    p = argparse.ArgumentParser(
        description="Process document's vector model"
    )
    p.add_argument(
        "--htmls-path",
        required=True,
        help="Directory containing html files"
    )
    p.add_argument(
        "--lemmas-path",
        required=True,
        help="Directory containing lemma files"
    )
    p.add_argument(
        "--tokens-path",
        required=True,
        help="Directory containing lemma files"
    )
    p.add_argument(
        "--output",
        required=True,
        help="Directory where results will be saved"
    )
    args = p.parse_args()

    evaluate_frequences(args.htmls_path, args.lemmas_path, args.tokens_path, args.output)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nABORTED")