"""Тестовое приложение UCAR<>TOPDOER"""

from datetime import datetime
import sqlite3

from flask import Flask, request, jsonify

app = Flask(__name__)
app.json.ensure_ascii = False  # type: ignore

def init_db():
    """Инициализирует базу данных, если она не существует."""
    conn = sqlite3.connect('reviews.db')
    conn.execute("PRAGMA encoding = 'UTF-8'")
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        sentiment TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

init_db()

def analyze_sentiment(text):
    """Функция определения настроения"""
    text_lower = text.lower()
    positive_words = {'хорош', 'отличн', 'прекрасн', 'люблю', 'нравится', 'супер', 'класс', 'восхитительн'}
    negative_words = {'плох', 'ужасн', 'ненавиж', 'отвратительн', 'кошмар', 'разочарован', 'недоволен'}

    # Проверяем сначала негатив на тот случай, если встречаются оба слова в одном отзыве
    # тем самым исключаем ошибочное определение позитивного отзыва
    if any(word in text_lower for word in negative_words):
        return 'negative'
    if any(word in text_lower for word in positive_words):
        return 'positive'
    return 'neutral'

@app.route('/reviews', methods=['POST'])
def add_review():
    """Добавляет отзыв в БД"""
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.get_json()
    if 'text' not in data:
        return jsonify({'error': 'Missing text field'}), 400

    text = data['text']
    sentiment = analyze_sentiment(text)
    created_at = datetime.utcnow().isoformat()

    conn = sqlite3.connect('reviews.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO reviews (text, sentiment, created_at) VALUES (?, ?, ?)',
        (text, sentiment, created_at)
    )
    review_id = cursor.lastrowid
    conn.commit()

    cursor.execute(
        'SELECT id, text, sentiment, created_at FROM reviews WHERE id = ?',
        (review_id,)
    )
    review = cursor.fetchone()
    conn.close()

    return jsonify({
        'id': review[0],
        'text': review[1],
        'sentiment': review[2],
        'created_at': review[3]
    }), 201

@app.route('/reviews', methods=['GET'])
def get_reviews():
    """Получить отзывы из БД"""
    sentiment_filter = request.args.get('sentiment')

    query = 'SELECT id, text, sentiment, created_at FROM reviews'
    params = ()

    if sentiment_filter:
        query += ' WHERE sentiment = ?'
        params = (sentiment_filter,)

    conn = sqlite3.connect('reviews.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    reviews = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            'id': review[0],
            'text': review[1],
            'sentiment': review[2],
            'created_at': review[3]
        }
        for review in reviews
    ])

if __name__ == '__main__':
    app.run(debug=True)
