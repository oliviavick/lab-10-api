
import logging
import html

from chalice import Chalice, NotFoundError, Response
from chalicelib.analyze import COLLECTION, DATABASE, analyze_book, connect

BUCKET = "public-oliviavick-lab06"

app = Chalice(app_name="book-analyzer")
logging.getLogger().setLevel(logging.INFO)


# Lab 07: Analyze newly uploaded books
@app.on_s3_event(
    bucket=BUCKET,
    events=["s3:ObjectCreated:*"],
    suffix=".txt"
)
def analyze_new_book(event):
    """Analyze a book when uploaded to S3."""
    analyze_book(event.bucket, event.key)


# Lab 10: API routes
BOOK_FIELDS = {"runs": 0, "llm_analysis.at": 0}


@app.route("/")
def index():
    """Return the number of books in the collection."""
    client = connect()
    try:
        count = client[DATABASE][COLLECTION].count_documents({})
    finally:
        client.close()
    return {"books": count}


@app.route("/books")
def list_books():
    """Return books sorted by title, optionally filtered by author."""
    params = app.current_request.query_params or {}
    query = {}

    if "author" in params:
        query["author"] = params["author"]

    client = connect()
    try:
        books = list(
            client[DATABASE][COLLECTION]
            .find(query, {"title": 1, "author": 1})
            .sort("title", 1)
        )
    finally:
        client.close()

    return books


@app.route("/books/{key}")
def get_book(key):
    """Return one book, or 404 if it does not exist."""
    client = connect()
    try:
        book = client[DATABASE][COLLECTION].find_one(
            {"_id": key}, BOOK_FIELDS
        )
    finally:
        client.close()

    if book is None:
        raise NotFoundError(f"No book with key {key}")

    return book


@app.route("/page")
def page():
    """Display the book list as a web page."""
    rows = []

    for book in list_books():
        key = html.escape(book["_id"])
        title = html.escape(book.get("title", "(no title)"))
        author = html.escape(book.get("author", "(unknown author)"))
        rows.append(
            f'<li><a href="books/{key}">{title}</a> by {author}</li>'
        )

    body = (
        "<!doctype html><title>My books</title>"
        "<h1>My books</h1><ul>"
        + "".join(rows)
        + "</ul>"
    )

    return Response(
        body=body,
        status_code=200,
        headers={"Content-Type": "text/html"}
    )

