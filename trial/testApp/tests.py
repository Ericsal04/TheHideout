from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.staticfiles import finders
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse


User = get_user_model()
TEST_PASSWORD = 'Lantern-bridge!4729'


class HomeTests(SimpleTestCase):
    def test_home_is_public_and_has_account_links(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'testApp/home.html')
        self.assertContains(response, reverse('register'))
        self.assertContains(response, reverse('login'))
        self.assertContains(response, 'Group finding is coming soon.')

    def test_home_rejects_post(self):
        self.assertEqual(self.client.post(reverse('home')).status_code, 405)

    def test_stylesheet_is_discoverable(self):
        self.assertIsNotNone(finders.find('testApp/css/style.css'))


class RegistrationTests(TestCase):
    def register(self, **overrides):
        data = {
            'username': 'new_player',
            'password1': TEST_PASSWORD,
            'password2': TEST_PASSWORD,
        }
        data.update(overrides)
        return self.client.post(reverse('register'), data)

    def test_registration_page_has_labeled_fields_and_csrf_token(self):
        response = self.client.get(reverse('register'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'testApp/register.html')
        self.assertContains(response, 'for="id_username"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_valid_registration_hashes_password_and_redirects_to_login(self):
        response = self.register()

        # Inspect the first login response before the one-time message is consumed.
        self.assertRedirects(response, reverse('login'), fetch_redirect_response=False)
        user = User.objects.get(username='new_player')
        self.assertTrue(user.check_password(TEST_PASSWORD))
        self.assertNotEqual(user.password, TEST_PASSWORD)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertContains(self.client.get(reverse('login')), 'Your account is ready.')

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user(username='new_player', password=TEST_PASSWORD)

        response = self.register()

        self.assertFormError(response.context['form'], 'username', 'A user with that username already exists.')
        self.assertEqual(User.objects.count(), 1)

    def test_password_mismatch_is_rejected(self):
        response = self.register(password2='Different-passphrase!72')

        self.assertIn('password2', response.context['form'].errors)
        self.assertFalse(User.objects.exists())

    def test_password_validators_reject_weak_passwords(self):
        for password in ['a9!', 'password', '739285016428', 'new_player']:
            with self.subTest(password=password):
                response = self.register(password1=password, password2=password)

                self.assertIn('password2', response.context['form'].errors)
                self.assertFalse(User.objects.exists())

    def test_empty_post_displays_required_errors(self):
        response = self.client.post(reverse('register'), {})

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'username', 'This field is required.')
        self.assertFormError(response.context['form'], 'password1', 'This field is required.')
        self.assertFormError(response.context['form'], 'password2', 'This field is required.')
        self.assertFalse(User.objects.exists())

    def test_invalid_username_is_rejected_and_escaped_in_html(self):
        response = self.register(username='<script>alert(1)</script>')

        self.assertIn('username', response.context['form'].errors)
        self.assertNotContains(response, '<script>')
        self.assertContains(response, '&lt;script&gt;')
        self.assertFalse(User.objects.exists())

    def test_authenticated_user_cannot_create_another_account(self):
        user = User.objects.create_user(username='existing_player', password=TEST_PASSWORD)
        self.client.force_login(user)
... (124 lines left)