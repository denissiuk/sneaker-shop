from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User, Sneaker, CartItem, Order
from datetime import datetime
import asyncio
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'

# Подключение к базе данных
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///shop.db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Создаем базу при запуске приложения
with app.app_context():
    db.create_all()
    # Создаем админа (если нет)
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        db.session.add(admin)
        db.session.commit()

# Добавляем CartItem в глобальный контекст шаблонов
@app.context_processor
def inject_cartitem():
    return dict(CartItem=CartItem)

# Импортируем бота после создания app
from bot import notify_admin

# Главная — каталог
@app.route('/')
def index():
    sneakers = Sneaker.query.all()
    return render_template('index.html', sneakers=sneakers)

# Админка — управление кроссовками
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('user_id'):
        flash('Требуется вход в систему.')
        return redirect('/login')
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        flash('Доступ запрещён. Только для администраторов.')
        return redirect('/')
    
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        image_url = request.form.get('image_url') or '/static/default.jpg'
        sneaker = Sneaker(name=name, price=price, image_url=image_url)
        db.session.add(sneaker)
        db.session.commit()
        flash('Кроссовки добавлены!')
        return redirect('/admin')
    
    sneakers = Sneaker.query.all()
    return render_template('admin.html', sneakers=sneakers)

# Редактирование товара
@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
def edit_sneaker(id):
    if not session.get('user_id'):
        return redirect('/login')
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        flash('Доступ запрещён.')
        return redirect('/')
    
    sneaker = Sneaker.query.get_or_404(id)
    
    if request.method == 'POST':
        sneaker.name = request.form['name']
        sneaker.price = float(request.form['price'])
        sneaker.image_url = request.form.get('image_url') or '/static/default.jpg'
        db.session.commit()
        flash('Товар обновлён!')
        return redirect('/admin')
    
    return render_template('edit_sneaker.html', sneaker=sneaker)

# Удаление товара
@app.route('/admin/delete/<int:id>', methods=['POST'])
def delete_sneaker(id):
    if not session.get('user_id'):
        return redirect('/login')
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        flash('Доступ запрещён.')
        return redirect('/')
    
    sneaker = Sneaker.query.get_or_404(id)
    db.session.delete(sneaker)
    db.session.commit()
    flash('Товар удалён!')
    return redirect('/admin')

@app.route('/edit_price/<int:id>', methods=['POST'])
def edit_price(id):
    if not session.get('user_id'):
        return redirect('/login')
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        flash('Доступ запрещён.')
        return redirect('/')
    
    sneaker = Sneaker.query.get(id)
    if sneaker:
        sneaker.price = float(request.form['price'])
        db.session.commit()
        flash('Цена обновлена!')
    return redirect('/admin')

# Логин (упрощённый)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()
        if user:
            session['user_id'] = user.id
            return redirect('/profile')
        else:
            # Создаём нового пользователя (для демо)
            user = User(username=username, email=f"{username}@example.com")
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            return redirect('/profile')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/')

# Личный кабинет
@app.route('/profile')
def profile():
    if not session.get('user_id'):
        return redirect('/login')
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

# Корзина
@app.route('/cart')
def cart():
    if not session.get('user_id'):
        return redirect('/login')
    user = User.query.get(session['user_id'])
    items = CartItem.query.filter_by(user_id=user.id).all()

    # Фильтруем только те элементы, у которых есть связанный Sneaker
    valid_items = []
    total = 0.0

    for item in items:
        sneaker = Sneaker.query.get(item.sneaker_id)
        if sneaker:
            valid_items.append(item)
            total += item.quantity * sneaker.price
        else:
            # Удаляем "битый" элемент из корзины
            db.session.delete(item)

    db.session.commit()

    return render_template('cart.html', items=valid_items, total=total)

# Добавить в корзину
@app.route('/add_to_cart/<int:sneaker_id>')
def add_to_cart(sneaker_id):
    if not session.get('user_id'):
        return redirect('/login')
    user_id = session['user_id']
    item = CartItem.query.filter_by(user_id=user_id, sneaker_id=sneaker_id).first()
    if item:
        item.quantity += 1
    else:
        item = CartItem(user_id=user_id, sneaker_id=sneaker_id, quantity=1)
        db.session.add(item)
    db.session.commit()
    return redirect('/cart')

# Удалить из корзины
@app.route('/remove_from_cart/<int:sneaker_id>')
def remove_from_cart(sneaker_id):
    if not session.get('user_id'):
        return redirect('/login')
    user_id = session['user_id']
    item = CartItem.query.filter_by(user_id=user_id, sneaker_id=sneaker_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect('/cart')

# Оформление заказа
@app.route('/checkout', methods=['POST'])
def checkout():
    if not session.get('user_id'):
        return redirect('/login')
    user_id = session['user_id']
    items = CartItem.query.filter_by(user_id=user_id).all()
    if not items:
        return redirect('/cart')

    full_name = request.form['full_name']
    phone = request.form['phone']
    address = request.form['address']
    delivery_cost = 12.0

    total = 0.0
    for item in items:
        sneaker = Sneaker.query.get(item.sneaker_id)
        if sneaker:
            total += item.quantity * sneaker.price
        else:
            db.session.delete(item)
    db.session.commit()

    total_with_delivery = total + delivery_cost

    order = Order(
        user_id=user_id,
        total=total_with_delivery,
        delivery_info=f"ФИО: {full_name}, Телефон: {phone}, Адрес: {address}, Доставка: {delivery_cost} руб."
    )
    db.session.add(order)
    db.session.delete(CartItem.query.filter_by(user_id=user_id))
    db.session.commit()

    print(f"🔔 НОВЫЙ ЗАКАЗ! Пользователь ID: {user_id}, сумма: {total_with_delivery} руб.")
    print(f"Данные доставки: {full_name}, {phone}, {address}")

    # Отправка уведомления в Telegram
    try:
        asyncio.run(notify_admin(
            f"🔔 НОВЫЙ ЗАКАЗ!\n"
            f"Сумма: {total_with_delivery} BYN\n"
            f"ФИО: {full_name}\n"
            f"Телефон: {phone}\n"
            f"Адрес: {address}"
        ))
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

    flash('Заказ оформлен! Админ уведомлён.')
    return redirect('/profile')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False  # ← ОБЯЗАТЕЛЬНО False на Render!
    )