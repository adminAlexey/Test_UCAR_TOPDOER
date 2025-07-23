"""Тестовое приложение UCAR<>TOPDOER"""

from datetime import datetime
import sqlite3
from enum import StrEnum

from flask import Flask, request, jsonify, current_app, g

app = Flask(__name__)
app.json.ensure_ascii = False  # type: ignore
app.config["DATABASE"] = "reviews.db"


def get_db():
    """Подключаемся к БД"""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    """Закрываем БД"""
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db() -> None:
    """Создаем БД"""
    db = get_db()
    db.execute("PRAGMA encoding = 'UTF-8'")
    cursor = db.cursor()
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        sentiment TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """
    )
    db.commit()


app.teardown_appcontext(close_db)


class Sentiment(StrEnum):
    """Константы для определения настроения"""

    NEGATIVE = "negative"
    POSITIVE = "positive"
    NEUTRAL = "neutral"


def analyze_sentiment(text: str) -> Sentiment:
    """Функция определения настроения"""
    text_lower = text.lower()
    positive_words = (
        "хорош",
        "отличн",
        "прекрасн",
        "люблю",
        "нравится",
        "супер",
        "класс",
        "восхитительн",
    )
    negative_words = (
        "плох",
        "ужасн",
        "ненавиж",
        "отвратительн",
        "кошмар",
        "разочарован",
        "недоволен",
    )

    # Проверяем сначала негатив на тот случай, если встречаются оба слова в одном отзыве
    # тем самым исключаем ошибочное определение позитивного отзыва
    if any(word in text_lower for word in negative_words):
        return Sentiment.NEGATIVE
    if any(word in text_lower for word in positive_words):
        return Sentiment.POSITIVE
    return Sentiment.NEUTRAL


@app.route("/reviews", methods=["POST"])
def add_review():
    """Добавляет отзыв в БД"""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    if "text" not in data:
        return jsonify({"error": "Missing text field"}), 400

    text = data["text"]
    sentiment = analyze_sentiment(text)
    created_at = datetime.now().isoformat()

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO reviews (text, sentiment, created_at) VALUES (?, ?, ?)",
        (text, sentiment, created_at),
    )
    review_id = cursor.lastrowid

    cursor.execute(
        "SELECT id, text, sentiment, created_at FROM reviews WHERE id = ?", (review_id,)
    )
    review = cursor.fetchone()
    db.commit()

    return (
        jsonify(
            {
                "id": review[0],
                "text": review[1],
                "sentiment": review[2],
                "created_at": review[3],
            }
        ),
        201,
    )


@app.route("/reviews", methods=["GET"])
def get_reviews():
    """Получить отзывы из БД"""
    sentiment = request.args.get("sentiment")

    query = "SELECT id, text, sentiment, created_at FROM reviews"
    params = ()

    if sentiment:
        sentiment_filter = Sentiment(sentiment)
        query += " WHERE sentiment = ?"
        params = (sentiment_filter,)

    db = get_db()
    cursor = db.cursor()
    cursor.execute(query, params)
    reviews = cursor.fetchall()
    db.commit()

    return (
        jsonify(
            [
                {
                    "id": review[0],
                    "text": review[1],
                    "sentiment": review[2],
                    "created_at": review[3],
                }
                for review in reviews
            ]
        ),
        200,
    )


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
