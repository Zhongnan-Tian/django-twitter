from testing.testcases import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User


LOGIN_URL = '/api/accounts/login/'
LOGOUT_URL = '/api/accounts/logout/'
SIGNUP_URL = '/api/accounts/signup/'
LOGIN_STATUS_URL = '/api/accounts/login_status/'


class AccountApiTests(TestCase):

    def setUp(self):
        # will be called by every test function
        self.client = APIClient()
        self.user = self.create_user(
            username='admin',
            email='admin@twitter.com',
            password='correct password',
        )

    def createUser(self, username, email, password):
        # cannot use User.objects.create()
        # because password needs to be hashed, username and email need some normalization
        return User.objects.create_user(username, email, password)

    def test_login(self):
        # every test function must start with test_
        # should not use get method
        response = self.client.get(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })
        # fail, http status code should be 405 = METHOD_NOT_ALLOWED
        self.assertEqual(response.status_code, 405)

        # post but wrong password
        response = self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'wrong password',
        })
        self.assertEqual(response.status_code, 400)

        # verify that user has not logged in yet
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], False)

        # login with correct password
        response = self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data['user'], None)
        self.assertEqual(response.data['user']['email'], 'admin@twitter.com')

        # verify that user has logged in
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

    def test_logout(self):
        # login first
        self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })
        # verify that user has been logged in
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

        # should not use get method
        response = self.client.get(LOGOUT_URL)
        self.assertEqual(response.status_code, 405)

        # use post to log out
        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.status_code, 200)

        # verify that user has been logged out
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], False)

    def test_signup(self):
        data = {
            'username': 'someone',
            'email': 'someone@twitter.com',
            'password': 'any password',
        }
        # should not use get method
        response = self.client.get(SIGNUP_URL, data)
        self.assertEqual(response.status_code, 405)

        # email should be valid
        response = self.client.post(SIGNUP_URL, {
            'username': 'someone',
            'email': 'not a correct email',
            'password': 'any password'
        })
        self.assertEqual(response.status_code, 400)

        # password should not be short
        response = self.client.post(SIGNUP_URL, {
            'username': 'someone',
            'email': 'someone@twitter.com',
            'password': '123',
        })
        self.assertEqual(response.status_code, 400)

        # username should not be too long
        response = self.client.post(SIGNUP_URL, {
            'username': 'username is tooooooooooooooooo loooooooong',
            'email': 'someone@twitter.com',
            'password': 'any password',
        })
        self.assertEqual(response.status_code, 400)

        # sign up
        response = self.client.post(SIGNUP_URL, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['user']['username'], 'someone')

        # verify that user has been logged in
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)
