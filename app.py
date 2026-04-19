from flask import Flask, render_template, request, redirect, url_for, Response, jsonify
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()  # must be before sentiment import

from sentiment import get_stock_sentiment

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

with app.app_context():
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS articles
                  (id INTEGER PRIMARY KEY, title TEXT, content TEXT,
                   filename TEXT, file_content TEXT, image_filename TEXT)''')
    db.commit()
    for col in ['filename', 'file_content', 'image_filename']:
        try:
            db.execute(f'ALTER TABLE articles ADD COLUMN {col} TEXT')
            db.commit()
        except Exception:
            pass

# ── EXISTING ROUTES ────────────────────────────────────────────────────────────

@app.route('/')
def home():
    db = get_db()
    articles = db.execute('SELECT * FROM articles').fetchall()
    return render_template('index.html', articles=articles)

@app.route('/article/<int:id>')
def article(id):
    db = get_db()
    post = db.execute('SELECT * FROM articles WHERE id=?', (id,)).fetchone()
    if not post:
        return 'Article not found.', 404
    return render_template('article.html', post=post)

@app.route('/post', methods=['GET', 'POST'])
def post():
    if request.method == 'POST':
        title          = request.form['title']
        content        = request.form['content']
        filename       = None
        file_content   = None
        image_filename = None

        file = request.files.get('file')
        if file and file.filename:
            filename     = file.filename
            file_content = file.read().decode('utf-8', errors='replace')

        image = request.files.get('image')
        if image and image.filename:
            ext            = image.filename.rsplit('.', 1)[-1].lower()
            image_filename = f"{os.urandom(8).hex()}.{ext}"
            image.save(os.path.join(UPLOAD_FOLDER, image_filename))

        db = get_db()
        db.execute(
            'INSERT INTO articles (title, content, filename, file_content, image_filename) VALUES (?, ?, ?, ?, ?)',
            (title, content, filename, file_content, image_filename)
        )
        db.commit()
        return redirect('/')
    return render_template('post.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    db   = get_db()
    post = db.execute('SELECT * FROM articles WHERE id=?', (id,)).fetchone()
    if not post:
        return 'Article not found.', 404

    if request.method == 'POST':
        title          = request.form['title']
        content        = request.form['content']
        image_filename = post['image_filename']

        if request.form.get('remove_image') == '1':
            if image_filename:
                old_path = os.path.join(UPLOAD_FOLDER, image_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            image_filename = None

        image = request.files.get('image')
        if image and image.filename:
            if image_filename:
                old_path = os.path.join(UPLOAD_FOLDER, image_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            ext            = image.filename.rsplit('.', 1)[-1].lower()
            image_filename = f"{os.urandom(8).hex()}.{ext}"
            image.save(os.path.join(UPLOAD_FOLDER, image_filename))

        db.execute(
            'UPDATE articles SET title=?, content=?, image_filename=? WHERE id=?',
            (title, content, image_filename, id)
        )
        db.commit()
        return redirect(url_for('article', id=id))

    return render_template('edit.html', post=post)

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    db   = get_db()
    post = db.execute('SELECT image_filename FROM articles WHERE id=?', (id,)).fetchone()
    if post and post['image_filename']:
        img_path = os.path.join(UPLOAD_FOLDER, post['image_filename'])
        if os.path.exists(img_path):
            os.remove(img_path)
    db.execute('DELETE FROM articles WHERE id=?', (id,))
    db.commit()
    return redirect('/')

@app.route('/download/<int:id>')
def download(id):
    db   = get_db()
    post = db.execute('SELECT filename, file_content FROM articles WHERE id=?', (id,)).fetchone()
    if not post or not post['filename']:
        return 'No file attached.', 404
    return Response(
        post['file_content'],
        mimetype='application/octet-stream',
        headers={'Content-Disposition': f'attachment; filename="{post["filename"]}"'}
    )

# ── SENTIMENT ROUTES ───────────────────────────────────────────────────────────

@app.route('/sentiment')
def sentiment_page():
    """Renders the sentiment dashboard page."""
    return render_template('sentiment.html')

@app.route('/api/sentiment')
def sentiment_api():
    """
    API endpoint. Called by frontend JS.
    GET /api/sentiment?stock=Zomato
    Returns JSON sentiment result.
    """
    stock = request.args.get('stock', '').strip()
    if not stock:
        return jsonify({"error": "No stock name provided."}), 400
    if len(stock) > 50:
        return jsonify({"error": "Stock name too long."}), 400

    result = get_stock_sentiment(stock)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
