from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Transport
from forms import LoginForm, RegisterForm, TransportForm
import os
from pathlib import Path

app = Flask(__name__, template_folder="templates")

# Создаём папку instance и используем абсолютный путь к БД
INSTANCE_DIR = Path(__file__).parent / 'instance'
INSTANCE_DIR.mkdir(exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{INSTANCE_DIR / "rental.db"}'
app.config['SECRET_KEY'] = 'super-secret-key-2026'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к странице.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    stats = {
        'total': Transport.query.count(),
        'available': Transport.query.filter_by(status='available').count(),
        'rented': Transport.query.filter_by(status='rented').count(),
        'maintenance': Transport.query.filter_by(status='maintenance').count(),
    }
    return render_template('index.html', stats=stats)

@app.route('/transports')
@login_required
def transports():
    # Получаем параметр фильтра из URL (?status=available и т.д.)
    status_filter = request.args.get('status')

    query = Transport.query
    if status_filter in ['available', 'rented', 'maintenance']:
        query = query.filter_by(status=status_filter)

    transports = query.all()

    return render_template('transport_list.html',
                           transports=transports,
                           current_filter=status_filter)

@app.route('/transport/add', methods=['GET', 'POST'])
@app.route('/transport/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def transport_edit(id=None):
    if not current_user.is_admin():
        flash('Доступ запрещён', 'error')
        return redirect(url_for('transports'))

    transport = Transport.query.get_or_404(id) if id else None
    form = TransportForm(obj=transport)

    if form.validate_on_submit():
        if not transport:
            transport = Transport()
            db.session.add(transport)

        form.populate_obj(transport)
        db.session.commit()
        flash('Транспорт сохранён', 'success')
        return redirect(url_for('transports'))

    return render_template('transport_edit.html', form=form, transport=transport)

@app.route('/users')
@login_required
def users_list():
    if not current_user.is_admin():
        flash('Доступ запрещён', 'error')
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Вход выполнен', 'success')
            return redirect(url_for('index'))
        flash('Неверные данные', 'error')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Пользователь существует', 'error')
        else:
            user = User(username=form.username.data, role='user')
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Регистрация успешна', 'success')
            return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли', 'info')
    return redirect(url_for('index'))

@app.route('/user/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def user_edit(id):
    if not current_user.is_admin():
        flash('Доступ запрещён', 'error')
        return redirect(url_for('users_list'))

    user = User.query.get_or_404(id)
    if request.method == 'POST':
        new_username = request.form['username']
        if User.query.filter_by(username=new_username).first() and new_username != user.username:
            flash('Это имя пользователя уже занято', 'error')
        else:
            user.username = new_username
            if request.form.get('password'):  # если пароль указан — меняем
                user.set_password(request.form['password'])
            db.session.commit()
            flash('Пользователь обновлён', 'success')
            return redirect(url_for('users_list'))

    return render_template('user_edit.html', user=user)

@app.route('/user/delete/<int:id>', methods=['POST'])
@login_required
def user_delete(id):
    if not current_user.is_admin():
        flash('Доступ запрещён', 'error')
        return redirect(url_for('users_list'))

    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('Нельзя удалить самого себя', 'error')
        return redirect(url_for('users_list'))

    db.session.delete(user)
    db.session.commit()
    flash('Пользователь удалён', 'success')
    return redirect(url_for('users_list'))

@app.route('/transport/delete/<int:id>', methods=['POST'])
@login_required
def transport_delete(id):
    if not current_user.is_admin():
        flash('Доступ запрещён', 'error')
        return redirect(url_for('transports'))

    transport = Transport.query.get_or_404(id)
    db.session.delete(transport)
    db.session.commit()
    flash('Транспорт удалён', 'success')
    return redirect(url_for('transports'))

if __name__ == '__main__':
    with app.app_context():  # Обязательно создаём контекст приложения
        db.create_all()       # Создаём таблицы
        # Создаём админа по умолчанию, если его нет
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)