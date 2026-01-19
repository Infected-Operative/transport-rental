from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, FloatField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class RegisterForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Пароль', validators=[DataRequired()])
    confirm = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

class TransportForm(FlaskForm):
    type = SelectField('Тип', choices=[('bicycle', 'Велосипед'), ('scooter', 'Самокат')], validators=[DataRequired()])
    model = StringField('Модель', validators=[DataRequired()])
    status = SelectField('Статус', choices=[('available', 'Доступен'), ('rented', 'Арендован'), ('maintenance', 'На обслуживании')], default='available')
    price_per_hour = FloatField('Цена за час (руб)', validators=[DataRequired()])
    location = StringField('Локация')
    submit = SubmitField('Сохранить')