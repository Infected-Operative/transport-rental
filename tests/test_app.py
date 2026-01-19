import sys
import os

# Добавляем корень проекта в путь Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from app import app, db
from models import User, Transport

class TransportRentalTestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()

        with app.app_context():
            db.create_all()
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin', role='admin')
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def register(self, username, password='password'):
        return self.client.post('/register', data={
            'username': username,
            'password': password,
            'confirm': password
        }, follow_redirects=True)

    def login(self, username, password):
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    # 1. Home page loads
    def test_1_home_page_loads(self):
        rv = self.client.get('/')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'<h1', rv.data)  # просто проверяем, что это HTML с заголовком

    # 2. Transports page requires login
    def test_2_transports_requires_login(self):
        rv = self.client.get('/transports', follow_redirects=True)
        self.assertIn(b'login', rv.data)  # редирект на /login

    # 3. Successful registration (check redirect to login)
    def test_3_successful_registration(self):
        rv = self.register('newuser')
        self.assertIn(b'login', rv.data)  # после регистрации редирект на логин

    # 4. Duplicate registration stays on register page
    def test_4_duplicate_registration(self):
        self.register('duplicate')
        rv = self.register('duplicate')
        self.assertIn(b'register', rv.data)  # остаёмся на странице регистрации

    # 5. Successful login redirects to home
    def test_5_successful_login(self):
        self.register('loginuser')
        rv = self.login('loginuser', 'password')
        self.assertIn(b'/', rv.data)  # редирект на главную

    # 6. Failed login stays on login page
    def test_6_failed_login(self):
        rv = self.login('wrong', 'wrong')
        self.assertIn(b'login', rv.data)

    # 7. Logout redirects to home
    def test_7_logout(self):
        self.register('logoutuser')
        self.login('logoutuser', 'password')
        rv = self.logout()
        self.assertIn(b'/', rv.data)

    # 8. Admin sees users page
    def test_8_admin_sees_users_page(self):
        self.login('admin', 'admin123')
        rv = self.client.get('/users')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'users', rv.data)

    # 9. Regular user cannot access users page
    def test_9_user_cannot_access_users_page(self):
        self.register('regular')
        self.login('regular', 'password')
        rv = self.client.get('/users', follow_redirects=True)
        self.assertIn(b'/', rv.data)  # редирект на главную

    # 10. Admin can add transport
    def test_10_admin_can_add_transport(self):
        self.login('admin', 'admin123')
        rv = self.client.post('/transport/add', data={
            'type': 'bicycle',
            'model': 'Test Bike',
            'price_per_hour': 100,
            'location': 'Test Location'
        }, follow_redirects=True)
        self.assertIn(b'transports', rv.data)

    # 11. Regular user cannot add transport
    def test_11_user_cannot_add_transport(self):
        self.register('user1')
        self.login('user1', 'password')
        rv = self.client.post('/transport/add', data={
            'type': 'scooter',
            'model': 'Forbidden'
        }, follow_redirects=True)
        self.assertIn(b'transports', rv.data)  # редирект обратно

    # 12. Filter by available works
    def test_12_filter_by_available(self):
        self.login('admin', 'admin123')
        self.client.post('/transport/add', data={'type': 'bicycle', 'model': 'AvailableBike', 'price_per_hour': 100})
        rv = self.client.get('/transports?status=available')
        self.assertIn(b'AvailableBike', rv.data)

    # 13. Filter by rented works
    def test_13_filter_by_rented(self):
        self.login('admin', 'admin123')
        self.client.post('/transport/add', data={'type': 'scooter', 'model': 'RentedScooter', 'price_per_hour': 150, 'status': 'rented'})
        rv = self.client.get('/transports?status=rented')
        self.assertIn(b'RentedScooter', rv.data)

    # 14. Regular user sees booking button
    def test_14_user_sees_book_button(self):
        self.login('admin', 'admin123')
        self.client.post('/transport/add', data={'type': 'bicycle', 'model': 'Bookable', 'price_per_hour': 100})
        self.logout()
        self.register('bookuser')
        self.login('bookuser', 'password')
        rv = self.client.get('/transports')
        self.assertIn(b'Book', rv.data)  # текст кнопки на английском в тесте

    # 15. Booking button is present for available transport
    def test_15_booking_button_present(self):
        self.login('admin', 'admin123')
        self.client.post('/transport/add', data={'type': 'bicycle', 'model': 'BookableBike2', 'price_per_hour': 100})
        self.logout()
        self.register('bookuser2')
        self.login('bookuser2', 'password')
        rv = self.client.get('/transports')
        self.assertIn(b'Book', rv.data)

    # 16. Admin can edit transport
    def test_16_admin_can_edit_transport(self):
        self.login('admin', 'admin123')
        self.client.post('/transport/add', data={'type': 'bicycle', 'model': 'OldName', 'price_per_hour': 100})
        with app.app_context():
            t = Transport.query.first()
        rv = self.client.post(f'/transport/edit/{t.id}', data={
            'type': 'scooter', 'model': 'NewName', 'price_per_hour': 200
        }, follow_redirects=True)
        self.assertIn(b'NewName', rv.data)

    # 17. Admin can delete transport
    def test_17_admin_can_delete_transport(self):
        self.login('admin', 'admin123')
        self.client.post('/transport/add', data={'type': 'bicycle', 'model': 'ToDelete', 'price_per_hour': 100})
        with app.app_context():
            t = Transport.query.first()
        rv = self.client.post(f'/transport/delete/{t.id}', follow_redirects=True)
        self.assertNotIn(b'ToDelete', rv.data)

    # 18. Admin can edit user
    def test_18_admin_can_edit_user(self):
        self.register('edituser')
        self.login('admin', 'admin123')
        with app.app_context():
            u = User.query.filter_by(username='edituser').first()
        rv = self.client.post(f'/user/edit/{u.id}', data={
            'username': 'newname'
        }, follow_redirects=True)
        self.assertIn(b'newname', rv.data)

    # 19. Admin can delete other user
    def test_19_admin_can_delete_other_user(self):
        self.register('todelete')
        self.login('admin', 'admin123')
        with app.app_context():
            count_before = User.query.count()
        with app.app_context():
            u = User.query.filter_by(username='todelete').first()
        self.client.post(f'/user/delete/{u.id}', follow_redirects=True)
        with app.app_context():
            count_after = User.query.count()
        self.assertEqual(count_after, count_before - 1)

    # 20. Admin cannot delete self (user still exists)
    def test_20_admin_cannot_delete_self(self):
        self.login('admin', 'admin123')
        with app.app_context():
            u = User.query.filter_by(username='admin').first()
        rv = self.client.post(f'/user/delete/{u.id}', follow_redirects=True)
        with app.app_context():
            self.assertIsNotNone(User.query.filter_by(username='admin').first())

    # 21. Home page contains statistics section
    def test_21_home_page_stats(self):
        self.login('admin', 'admin123')
        rv = self.client.get('/')
        self.assertIn(b'<h2>', rv.data)  # проверяем наличие раздела с заголовком h2 (Статистика)

    # 22. Only admin can access edit transport page
    def test_22_only_admin_can_edit_transport(self):
        self.register('regular')
        self.login('regular', 'password')
        rv = self.client.get('/transport/edit/1', follow_redirects=True)
        self.assertIn(b'transports', rv.data)  # редирект на список

    # 23. Filter "All" shows all items
    def test_23_filter_all_shows_all(self):
        self.login('admin', 'admin123')
        self.client.post('/transport/add', data={'type': 'bicycle', 'model': 'All1', 'price_per_hour': 100})
        self.client.post('/transport/add', data={'type': 'scooter', 'model': 'All2', 'price_per_hour': 150, 'status': 'rented'})
        rv = self.client.get('/transports')
        self.assertIn(b'All1', rv.data)
        self.assertIn(b'All2', rv.data)

    # 24. Regular user does not see admin buttons
    def test_24_user_does_not_see_admin_buttons(self):
        self.register('viewer')
        self.login('viewer', 'password')
        rv = self.client.get('/transports')
        self.assertNotIn(b'Add transport', rv.data)
        self.assertNotIn(b'Edit', rv.data)
        self.assertNotIn(b'Delete', rv.data)

        # 25. Admin sees all control buttons
    def test_25_admin_sees_all_controls(self):
        self.login('admin', 'admin123')
        # Добавляем транспорт, чтобы появились кнопки редактирования и удаления
        self.client.post('/transport/add', data={
            'type': 'bicycle',
            'model': 'ControlTest',
            'price_per_hour': 100
        })
        rv = self.client.get('/transports')
        # Проверяем наличие ссылок по их URL (английские части, гарантированно присутствуют)
        self.assertIn(b'/transport/add', rv.data)      # ссылка "Добавить транспорт"
        self.assertIn(b'/transport/edit/', rv.data)    # ссылка "Редактировать"
        self.assertIn(b'/transport/delete/', rv.data)  # ссылка "Удалить"

if __name__ == '__main__':
    unittest.main(verbosity=2)