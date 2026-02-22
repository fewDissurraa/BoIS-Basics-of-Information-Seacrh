import argparse
import os
import re

class SearchEngine:
    def __init__(self, index_path, lemmas_path, htmls_path):
        print("Инициализация документов/индексов")
        self.inverted_index = self._load_inverted_index(index_path)
        self.lemmas = self._load_lemmas(lemmas_path)
        self.htmls = self._load_htmls(htmls_path)
        print("Документы/индексы инициализированны")

    def _load_inverted_index(self, index_path) -> dict[str, set[int]]:
        with open(index_path, 'r', encoding='utf-8') as file:
            inverted_index = {}
            for line in file.readlines():
                splitted = line.split()
                lemma = splitted[0]
                file_indexes = set(map(int, splitted[1:]))
                inverted_index[lemma] = file_indexes
            return inverted_index

    def _load_lemmas(self, lemmas_path) -> dict[str, set[str]]:
        lemmas_index = {}
        for filename in os.listdir(lemmas_path):
            filepath = os.path.join(lemmas_path, filename)
            with open(filepath, 'r', encoding='utf-8') as file:
                for line in file.readlines():
                    splitted = line.split()
                    lemma = splitted[0]
                    tokens = set(splitted[1:])
                    if lemma not in lemmas_index:
                        lemmas_index[lemma] = set()
                    for token in tokens:
                        lemmas_index[lemma].add(token)
        return lemmas_index

    def _load_htmls(self, htmls_path) -> dict[int, str]:
        htmls_index = {}
        pattern = re.compile(r'(\d+)\.html$')
        for filename in os.listdir(htmls_path):
            match = pattern.match(filename)
            if match:
                number = int(match.group(1))
                filepath = os.path.join(htmls_path, filename)
                htmls_index[number] = filepath
        return htmls_index

    def _tokenize_query(self, query: str) -> list[str]:
        # Регулярка ищет скобки, ключевые слова (AND, OR, NOT) или обычные слова
        token_pattern = r'\(|\)|\bAND\b|\bOR\b|\bNOT\b|\w+'
        tokens = re.findall(token_pattern, query, re.IGNORECASE)
        return [t.upper() if t.upper() in ['AND', 'OR', 'NOT', '(', ')'] else t.lower() for t in tokens]

    def _to_postfix(self, tokens: list[str]) -> list[str]:
        precedence = {'NOT': 3, 'AND': 2, 'OR': 1}
        output_queue = []
        operator_stack = []

        for token in tokens:
            if token not in precedence and token not in ['(', ')']:
                # Если это слово
                output_queue.append(token)
            elif token == '(':
                operator_stack.append(token)
            elif token == ')':
                while operator_stack and operator_stack[-1] != '(':
                    output_queue.append(operator_stack.pop())
                if operator_stack and operator_stack[-1] == '(':
                    operator_stack.pop()  # Удаляем '('
            else:
                # Если это оператор (AND, OR, NOT)
                while (operator_stack and
                       operator_stack[-1] != '(' and
                       precedence.get(operator_stack[-1], 0) >= precedence[token]):
                    output_queue.append(operator_stack.pop())
                operator_stack.append(token)

        while operator_stack:
            output_queue.append(operator_stack.pop())

        return output_queue

    def _get_indexes_by_token( self, token: str, default_value: set[int]) -> set[int]:
        if token in self.inverted_index:
            return self.inverted_index.get(token)

        for lemma, tokens in self.lemmas.items():
            if token in tokens:
                return self.inverted_index.get(lemma)

        return default_value

    def process_query(self, query: str) -> list[str]:
        tokens = self._tokenize_query(query)
        postfix_tokens = self._to_postfix(tokens)
        stack: list[set[int]] = []
        all_docs = set(self.htmls.keys())

        for token in postfix_tokens:
            if token in ['AND', 'OR', 'NOT']:
                if token == 'NOT':
                    if not stack:
                        raise ValueError("Ошибка в запросе: оператору NOT не хватает операнда")
                    operand = stack.pop()
                    res = all_docs - operand
                    stack.append(res)
                else:
                    if len(stack) < 2:
                        raise ValueError("Ошибка в запросе: бинарному оператору не хватает операндов")
                    right = stack.pop()
                    left = stack.pop()

                    if token == 'AND':
                        res = left & right
                    elif token == 'OR':
                        res = left | right
                    stack.append(res)
            else:
                docs = self._get_indexes_by_token(token, set())
                stack.append(docs)

        if len(stack) != 1:
            raise ValueError("Ошибка в структуре запроса")

        return [self.htmls.get(idx) for idx in sorted(list(stack[0]))]


def main():
    p = argparse.ArgumentParser(
        description="Process lemmas: building inverted index"
    )
    p.add_argument(
        "--index-path",
        required=True,
        help="File path to inverted index"
    )
    p.add_argument(
        "--lemmas-path",
        required=True,
        help="Directory that contains lemma files"
    )
    p.add_argument(
        "--htmls-path",
        required=True,
        help="Directory that contains html files"
    )
    args = p.parse_args()
    search_engine = SearchEngine(args.index_path, args.lemmas_path, args.htmls_path)

    while True:
        query = input("Write query: ")
        if query == "":
            break
        results = search_engine.process_query(query)
        print("\n".join(results))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nABORTED")