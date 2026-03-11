from flask import Flask, render_template, request

from search import SearchEngine

app = Flask(__name__)

# Инициализация поисковой системы с путями к индексам
search_engine = SearchEngine(
    html_index_path="1_crawler/artefacts/dump/index.txt",
    lemmas_tfidf_path="4_tf_idf/artefacts/dump/lemmas",
    inverted_index_path="3_indexation/artefacts/dump/inverted_index.txt"
)


@app.route('/', methods=['GET', 'POST'])
def index():
    """Главная страница с формой поиска"""
    if request.method == 'POST':
        search_query = request.form.get('query', '').strip()
        
        # Валидация поискового запроса
        if not search_query:
            return render_template('index.html', error='Пожалуйста, введите поисковый запрос')
        
        # Выполнение поиска
        results = search_engine.process_search_query(search_query)
        
        # Получение топ 10 результатов
        top_results = results[:10]
        
        return render_template('results.html', 
                             query=search_query, 
                             results=top_results,
                             total_results=len(results))
    
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
