from django.test import TestCase
from accounts.models import User, BankAccount, Transaction
from accounts.forms import UserRegistrationForm
from django.urls import reverse


class UserModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="securepassword123",
            email_verified=True,
            date_of_birth="1990-01-01",
            first_name="Test",
            last_name="User",
            phone_number="1234567890",
            gender="Male",
            street="123 Test Street",
            zip_code="12345",
            country="Testland",
            state="Teststate",
            city="Testcity"
        )

    def test_user_creation(self):
        self.assertEqual(self.user.username, "testuser")
        self.assertTrue(self.user.email_verified)


class TransactionModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="securepassword123",
            date_of_birth="1990-01-01",
            first_name="Test",
            last_name="User",
            phone_number="1234567890",
            gender="Male",
            street="123 Test Street",
            zip_code="12345",
            country="Testland",
            state="Teststate",
            city="Testcity"
        )
        self.account = BankAccount.objects.create(
            user=self.user,
            account_type="Savings",
            balance=1000.00
        )
        self.transaction = Transaction.objects.create(
            account=self.account,
            amount=100.0,
            description="Test Deposit",
            type="credit"
        )

    def test_transaction_creation(self):
        self.assertEqual(self.transaction.amount, 100.0)
        self.assertEqual(self.transaction.type, "credit")
        self.assertEqual(self.transaction.account, self.account)


class LoginViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="securepassword123",
            date_of_birth="1990-01-01",
            first_name="Test",
            last_name="User",
            phone_number="1234567890",
            gender="Male",
            street="123 Test Street",
            zip_code="12345",
            country="Testland",
            state="Teststate",
            city="Testcity"
        )

    def test_login_view_get(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')


    def test_login_view_post_success(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'securepassword123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login

    def test_login_view_post_failure(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid credentials")


class RegisterViewTestCase(TestCase):
    def test_register_view_get(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')


    def test_register_view_post_success(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'securepassword123',
            'password2': 'securepassword123',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '1234567890',
            'gender': 'Male',
            'date_of_birth': '1990-01-01',
            'street': '123 Test Street',
            'zip_code': '12345',
            'country': 'Testland',
            'state': 'Teststate',
            'city': 'Testcity'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after registration
        self.assertTrue(User.objects.filter(username='newuser').exists())


class RegistrationFormTestCase(TestCase):
    def test_valid_form(self):
        form = UserRegistrationForm(data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'securepassword123',
            'password2': 'securepassword123',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '1234567890',
            'gender': 'Male',
            'date_of_birth': '1990-01-01',
            'street': '123 Test Street',
            'zip_code': '12345',
            'country': 'Testland',
            'state': 'Teststate',
            'city': 'Testcity'
        })
        self.assertTrue(form.is_valid())

    def test_invalid_form_password_mismatch(self):
        form = UserRegistrationForm(data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'securepassword123',
            'password2': 'differentpassword',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '1234567890',
            'gender': 'Male',
            'date_of_birth': '1990-01-01',
            'street': '123 Test Street',
            'zip_code': '12345',
            'country': 'Testland',
            'state': 'Teststate',
            'city': 'Testcity'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)


class TransactionTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="securepassword123",
            date_of_birth="1990-01-01",
            first_name="Test",
            last_name="User",
            phone_number="1234567890",
            gender="Male",
            street="123 Test Street",
            zip_code="12345",
            country="Testland",
            state="Teststate",
            city="Testcity"
        )
        self.account = BankAccount.objects.create(
            user=self.user,
            account_type="Savings",
            balance=1000.00
        )

    def test_deposit_transaction(self):
        transaction = Transaction.objects.create(
            account=self.account,
            amount=500.0,
            description="Test Deposit",
            type="credit"
        )
        self.assertEqual(transaction.amount, 500.0)
        self.assertEqual(transaction.type, "credit")

    def test_transfer_transaction(self):
        transaction = Transaction.objects.create(
            account=self.account,
            amount=200.0,
            description="Test Transfer",
            type="debit"
        )
        self.assertEqual(transaction.amount, 200.0)
        self.assertEqual(transaction.type, "debit")