import argparse
import os
import re
import sys
from dataclasses import dataclass
from typing import List, Set, Dict, Optional

import nltk
from bs4 import BeautifulSoup
from pymorphy2 import MorphAnalyzer


# Загрузка стоп-слов для русского языка
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

from nltk.corpus import stopwords

RUSSIAN_STOPWORDS = set(stopwords.words('russian'))


@dataclass
class ProcessingResult:
    """Результат обработки одного HTML файла."""
    html_file: str
    tokens_count: int
    lemmas_count: int
    error: Optional[str] = None


def extract_text_from_html(html_path: str) -> str:
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

    return text


def tokenize_text(text: str) -> List[str]:
    """
    Разбивает текст на токены, удаляя дубликаты, стоп-слова, числа и мусор.

    Args:
        text: Исходный текст.

    Returns:
        Список уникальных токенов.
    """
    # Разбиваем текст на слова, оставляем только кириллические буквы
    tokens = re.findall(r"[а-яА-ЯёЁ]+", text.lower())

    # Удаляем дубликаты
    unique_tokens: Set[str] = set(tokens)

    # Фильтруем токены
    filtered_tokens: List[str] = []
    for token in unique_tokens:
        # Пропускаем стоп-слова
        if token in RUSSIAN_STOPWORDS:
            continue

        # Пропускаем числа (токены, состоящие только из цифр)
        if token.isdigit():
            continue

        # Пропускаем мусор (слова содержащие одновременно буквы и цифры)
        if any(c.isdigit() for c in token):
            continue

        # Пропускаем слишком короткие токены (менее 2 символов)
        if len(token) < 2:
            continue

        filtered_tokens.append(token)

    return sorted(filtered_tokens)


def lemmatize_tokens(tokens: List[str]) -> Dict[str, List[str]]:
    """
    Группирует токены по леммам с использованием pymorphy2.

    Args:
        tokens: Список токенов.

    Returns:
        Словарь, где ключ - лемма, значение - список токенов.
    """
    morph = MorphAnalyzer()
    lemmas_dict: Dict[str, List[str]] = {}

    for token in tokens:
        parsed = morph.parse(token)[0]
        lemma = parsed.normal_form

        if lemma not in lemmas_dict:
            lemmas_dict[lemma] = []
        lemmas_dict[lemma].append(token)

    return lemmas_dict


def save_tokens(tokens: List[str], output_path: str) -> None:
    """
    Сохраняет токены в файл.

    Args:
        tokens: Список токенов.
        output_path: Путь к выходному файлу.
    """
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        for token in tokens:
            f.write(f"{token}\n")


def save_lemmas(lemmas_dict: Dict[str, List[str]], output_path: str) -> None:
    """
    Сохраняет леммы и соответствующие токены в файл.

    Args:
        lemmas_dict: Словарь лемм и токенов.
        output_path: Путь к выходному файлу.
    """
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        for lemma, tokens in sorted(lemmas_dict.items()):
            line = f"{lemma} {' '.join(tokens)}\n"
            f.write(line)


def process_html_file(html_path: str, output_dir: str) -> ProcessingResult:
    """
    Обрабатывает один HTML файл: извлекает текст, токенизирует и лемматизирует.

    Args:
        html_path: Путь к HTML файлу.
        output_dir: Директория для сохранения результатов.

    Returns:
        Результат обработки.
    """
    try:
        # Извлекаем текст из HTML
        text = extract_text_from_html(html_path)

        # Токенизируем текст
        tokens = tokenize_text(text)

        # Лемматизируем токены
        lemmas_dict = lemmatize_tokens(tokens)

        # Получаем номер HTML файла (например, 0001 из 0001.html)
        html_filename = os.path.basename(html_path)
        file_number = os.path.splitext(html_filename)[0]

        # Сохраняем токены
        tokens_path = os.path.join(output_dir, "tokens", f"tokens_{file_number}.txt")
        save_tokens(tokens, tokens_path)

        # Сохраняем леммы
        lemmas_path = os.path.join(output_dir, "lemmas", f"lemmas_{file_number}.txt")
        save_lemmas(lemmas_dict, lemmas_path)

        return ProcessingResult(
            html_file=html_path,
            tokens_count=len(tokens),
            lemmas_count=len(lemmas_dict),
            error=None,
        )

    except Exception as e:
        return ProcessingResult(
            html_file=html_path,
            tokens_count=0,
            lemmas_count=0,
            error=str(e),
        )


def process_html_directory(input_dir: str, output_dir: str) -> List[ProcessingResult]:
    """
    Обрабатывает все HTML файлы в указанной директории.

    Args:
        input_dir: Путь к директории с HTML файлами.
        output_dir: Путь к директории для сохранения результатов.

    Returns:
        Список результатов обработки.
    """
    if not os.path.isdir(input_dir):
        print(f"[ERROR] Directory not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    # Создаём выходную директорию, если она не существует
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "tokens"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "lemmas"), exist_ok=True)

    # Получаем все HTML файлы
    html_files = [
        os.path.join(input_dir, f)
        for f in os.listdir(input_dir)
        if f.endswith(".html")
    ]

    if not html_files:
        print(f"[ERROR] No HTML files found in: {input_dir}", file=sys.stderr)
        sys.exit(1)

    html_files.sort()
    results: List[ProcessingResult] = []

    print(f"[INFO] Processing {len(html_files)} HTML files...")
    print(f"[INFO] Output directory: {output_dir}")

    for i, html_file in enumerate(html_files, 1):
        print(f"[{i}/{len(html_files)}] Processing: {os.path.basename(html_file)}")
        result = process_html_file(html_file, output_dir)
        results.append(result)

        if result.error:
            print(f"  [ERROR] {result.error}")
        else:
            print(f"  [OK] Tokens: {result.tokens_count}, Lemmas: {result.lemmas_count}")

    return results


def main() -> None:
    p = argparse.ArgumentParser(
        description="Process HTML files: extract content, tokenize and lemmatize"
    )
    p.add_argument(
        "--input",
        required=True,
        help="Directory containing HTML files to process"
    )
    p.add_argument(
        "--output",
        required=True,
        help="Directory to save processed results (tokens and lemmas files)"
    )
    args = p.parse_args()

    results = process_html_directory(args.input, args.output)

    # Статистика
    successful = [r for r in results if r.error is None]
    failed = [r for r in results if r.error is not None]

    print(f"\n[OK] Successfully processed: {len(successful)} files")
    if failed:
        print(f"[WARN] Failed: {len(failed)} files")
        for r in failed:
            print(f"  - {os.path.basename(r.html_file)}: {r.error}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nABORTED")
