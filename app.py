"""A small Flask + SQLite storefront. Run with: python app.py."""
import os
from pathlib import Path
import secrets
import sqlite3
from functools import wraps

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(g.app_db)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get('SHOP_SECRET_KEY') or secrets.token_hex(32),
        DATABASE=os.environ.get('SHOP_DB_PATH') or str(Path(__file__).parent / 'data/shop.db'),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    if config:
        app.config.update(config)
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        g.app_db = app.config['DATABASE']
        db = get_db()
        db.executescript(Path(__file__).with_name('schema.sql').read_text())
        db.close()

    @app.teardown_appcontext
    def close_db(error=None):
        db = g.pop('db', None)
        if db is not None:
            db.close()

    @app.before_request
    def load_user():
        g.app_db = app.config['DATABASE']
        g.user = get_db().execute('SELECT id, username FROM users WHERE id = ?',
                                  (session.get('user_id'),)).fetchone()
        session.setdefault('csrf', secrets.token_hex(32))
        if request.method == 'POST':
            supplied = request.form.get('csrf', '')
            if not secrets.compare_digest(session['csrf'].encode(), supplied.encode()):
                abort(400, '表单已过期，请刷新页面后重试。')

    @app.template_filter('money')
    def money(value):
        return f'¥{value // 100}.{value % 100:02d}'

    @app.get('/')
    def index():
        q = request.args.get('q', '').strip()
        products = get_db().execute(
            'SELECT * FROM products WHERE name LIKE ? OR description LIKE ? ORDER BY id',
            (f'%{q}%', f'%{q}%'),
        ).fetchall()
        return render_template('index.html', products=products, q=q)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            if not 1 <= len(username) <= 40 or not 8 <= len(password) <= 128:
                flash('用户名为 1–40 字，密码为 8–128 字。')
            else:
                try:
                    with get_db() as db:
                        db.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                                   (username, generate_password_hash(password)))
                except sqlite3.IntegrityError:
                    flash('用户名已存在。')
                else:
                    flash('注册成功，请登录。')
                    return redirect(url_for('login'))
        return render_template('auth.html', registering=True)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            user = get_db().execute('SELECT * FROM users WHERE username = ?',
                                    (request.form.get('username', '').strip(),)).fetchone()
            if user and check_password_hash(user['password_hash'], request.form.get('password', '')):
                session.clear()
                session['user_id'] = user['id']
                return redirect(url_for('index'))
            flash('用户名或密码错误。')
        return render_template('auth.html', registering=False)

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index'))

    def cart_items():
        return get_db().execute(
            'SELECT p.*, c.quantity FROM cart c JOIN products p ON p.id = c.product_id '
            'WHERE c.user_id = ? ORDER BY p.id', (g.user['id'],),
        ).fetchall()

    @app.route('/cart', methods=['GET', 'POST'])
    @login_required
    def cart():
        if request.method == 'POST':
            try:
                pid = int(request.form.get('product_id', ''))
                quantity = int(request.form.get('quantity', ''))
            except ValueError:
                abort(400)
            if not 1 <= pid <= 2147483647 or not 0 <= quantity <= 99:
                abort(400)
            with get_db() as db:
                if not db.execute('SELECT id FROM products WHERE id = ?', (pid,)).fetchone():
                    abort(404)
                if quantity == 0:
                    db.execute('DELETE FROM cart WHERE user_id = ? AND product_id = ?', (g.user['id'], pid))
                else:
                    db.execute(
                        'INSERT INTO cart VALUES (?, ?, ?) ON CONFLICT(user_id, product_id) '
                        'DO UPDATE SET quantity = excluded.quantity', (g.user['id'], pid, quantity),
                    )
            return redirect(url_for('cart'))
        items = cart_items()
        return render_template('cart.html', items=items,
                               total=sum(i['price_cents'] * i['quantity'] for i in items))

    @app.post('/checkout')
    @login_required
    def checkout():
        with get_db() as db:
            db.execute('BEGIN IMMEDIATE')
            items = cart_items()
            if not items:
                flash('购物车为空，请先添加商品。')
                return redirect(url_for('cart'))
            total = sum(i['price_cents'] * i['quantity'] for i in items)
            oid = db.execute('INSERT INTO orders (user_id, total_cents) VALUES (?, ?)',
                             (g.user['id'], total)).lastrowid
            db.executemany('INSERT INTO order_items VALUES (?, ?, ?, ?)',
                           [(oid, i['name'], i['price_cents'], i['quantity']) for i in items])
            db.execute('DELETE FROM cart WHERE user_id = ?', (g.user['id'],))
        flash(f'订单 #{oid} 已创建，本演示不收取付款。')
        return redirect(url_for('orders'))

    @app.get('/orders')
    @login_required
    def orders():
        rows = get_db().execute('SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC',
                                (g.user['id'],)).fetchall()
        orders = [dict(row, items=get_db().execute(
            'SELECT * FROM order_items WHERE order_id = ?', (row['id'],)).fetchall()) for row in rows]
        return render_template('orders.html', orders=orders)

    @app.get('/orders/<int:oid>')
    @login_required
    def order_detail(oid):
        if not 1 <= oid <= 2147483647:
            abort(404)
        row = get_db().execute('SELECT * FROM orders WHERE id = ?', (oid,)).fetchone()
        if row is None:
            abort(404)
        order = dict(row, items=get_db().execute(
            'SELECT * FROM order_items WHERE order_id = ?', (oid,)).fetchall())
        return render_template('orders.html', orders=[order])

    return app


if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=5000, debug=False)
