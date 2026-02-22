import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ProcessingResult:
    file_path: str
    error: str

def resolve_output(output: str) -> Path:
    path = Path(output)

    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    counter = 1
    while True:
        new_filename = f"{stem}_{counter}{suffix}"
        new_path = parent / new_filename

        if not new_path.exists():
            print(f"[INFO] File on the path {output} already exists")
            print(f"Result file will be saved on path {str(new_path)}")
            return new_path

        counter += 1


def get_lemmas_file_paths(lemmas_path: str) -> dict[int, str]:
    lemmas_files = {}
    pattern = re.compile(r'lemmas_(\d+)\.txt$')

    for filename in os.listdir(lemmas_path):
        match = pattern.match(filename)
        if match:
            number = int(match.group(1))
            filepath = os.path.join(lemmas_path, filename)
            lemmas_files[number] = filepath

    return lemmas_files

def get_lemmas_from_lemma_file(lemma_file_path: str) -> list[str]:
    lemmas = []
    with open(lemma_file_path, 'r', encoding='utf-8') as file:
        for line in file.readlines():
            lemmas.append(line.split(maxsplit=1)[0])
        return lemmas

def process_lemmas_directory(lemmas_path: str, output: str) -> ProcessingResult:
    try:
        lemmas_file_paths = get_lemmas_file_paths(lemmas_path)
        if not lemmas_file_paths:
            return ProcessingResult(
                file_path=None,
                error="Input directory is empty or has files with invalid format"
            )
        resolved_output = resolve_output(output)

        lemma_to_file_indexes: dict[str, list[str]] = {}
        for file_index, lemma_file_path in lemmas_file_paths.items():
            lemmas = get_lemmas_from_lemma_file(lemma_file_path)
            for lemma in lemmas:
                if lemma not in lemma_to_file_indexes:
                    lemma_to_file_indexes[lemma] = []

                lemma_to_file_indexes[lemma].append(file_index)

        if not resolved_output.exists():
            resolved_output.parent.mkdir(parents=True, exist_ok=True)
            resolved_output.touch()
        with resolved_output.open('w') as file:
            for lemma, file_indexes in lemma_to_file_indexes.items():
                string_to_write = lemma + " " + " ".join(map(str, file_indexes)) + "\n"
                file.write(string_to_write)
        return ProcessingResult(file_path=str(resolved_output), error=None)
    except Exception as e:
        return ProcessingResult(file_path=None, error=str(e))



def main():
    p = argparse.ArgumentParser(
        description="Process lemmas: building inverted index"
    )
    p.add_argument(
        "--input",
        required=True,
        help="Directory containing lemmas files"
    )
    p.add_argument(
        "--output",
        required=True,
        help="File path to save processed results"
    )
    args = p.parse_args()

    result = process_lemmas_directory(args.input, args.output)
    if result.error:
        print(f"[ERROR] Something went wrong: {result.error}")
    else:
        print(f"[INFO] Inverted index has been created on the path {result.file_path}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nABORTED")