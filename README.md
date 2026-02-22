# BoIS-Basics-of-Information-Seacrh

Репозиторий для выполнения заданий по дисциплине "Основы информационного поиска"
Студенты: Фарукшин Эрнэст 11-202, Каюмов Расим 11-202

## Задание 1

Код краулера, архив со страницами и файл index.txt находятся в папке 1_crawler.

### Запуск

1. Установить зависимости
```shell
pip install -r requirements.txt
```

2. Запуск загрузчика страниц
```shell
python 1_crawler/crawler.py --urls 1_crawler/urls.txt --out 1_crawler/dump --need 100 --workers 6 --delay 0.6 --timeout 30
```
Параметры:

- --urls - путь к файлу с ссылками на страницы, которые требуется выгрузить
- --out - путь к директории куда будут сохранены страницы и файл index.txt
- --need - требуемое количество страниц
- --workers - количество потоков для выгрузки
- --delay - ожидание перед очередным запросом на хост
- --timeout - таймаут ожидания ответа от сервера


## Задание 2

Код находится в папке 2_tonkenize. Итог токенизации и лемматизации в папке 2_tonkenize/artefacts/dump

### Запуск

1. Установить зависимости
```shell
pip install -r requirements.txt
```

2. Запуск загрузчика страниц
```shell
python 2_tonkenize/html_processor.py --input 1_crawler/artefacts/dump/pages/ --output 2_tonkenize/processed/
```
Параметры:

- --input - путь к директории с html файлами
- --output- путь к директории куда будут сохранены результаты

## Задание 3

Код находится в папке 3_indexation. Итог индексации в папке 3_indexation/artefacts/dump

### Запуск

1. Установить зависимости
```shell
pip install -r requirements.txt
```

2. Запуск индексации
```shell
python 3_indexation/inverted_index.py --input 2_tonkenize/artefacts/dump/processed/lemmas --output 3_indexation/artefacts/dump/inverted_index.txt
```
Параметры:

- --input - путь к директории с леммами
- --output - путь к директории куда будут сохранены результаты

3. Запуск булева поиска
```shell
python 3_indexation/boolean_search.py --index-path 3_indexation/artefacts/dump/inverted_index.txt --lemmas-path 2_tonkenize/artefacts/dump/processed/lemmas --htmls-path 1_crawler/artefacts/dump/pages
```
Параметры:

- --index-path - путь к файлы инвертированного индекса
- --lemmas-path - путь к директории с леммами
- --htmls-path - путь к директории с html файлами
