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

        self.assertRedirects(self.client.get(reverse('register')), reverse('home'))
        self.assertRedirects(self.register(), reverse('home'))
        self.assertEqual(User.objects.count(), 1)

    def test_registration_rejects_unsupported_methods(self):
        self.assertEqual(self.client.put(reverse('register')).status_code, 405)
        self.assertFalse(User.objects.exists())


class AuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='hideout_player', password=TEST_PASSWORD)

    def log_in(self, **overrides):
        data = {'username': self.user.username, 'password': TEST_PASSWORD}
        data.update(overrides)
        return self.client.post(reverse('login'), data)

    def test_login_page_renders(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'testApp/login.html')

    def test_valid_login_creates_session_and_shows_member_navigation(self):
        response = self.log_in()

        self.assertRedirects(response, reverse('home'))
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        home = self.client.get(reverse('home'))
        self.assertContains(home, self.user.username)
        self.assertContains(home, 'Log out')
        self.assertNotContains(home, 'href="' + reverse('register') + '"')

    def test_invalid_credentials_display_error_without_session(self):
        response = self.log_in(password='incorrect-password')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].non_field_errors())
        self.assertContains(response, 'Please enter a correct username and password.')
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])

        response = self.log_in()

        self.assertTrue(response.context['form'].non_field_errors())
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_login_preserves_and_accepts_a_local_next_destination(self):
        destination = reverse('home') + '?from=login'
        response = self.client.get(reverse('login'), {'next': destination})
        self.assertContains(response, 'name="next" value="' + destination + '"')

        self.assertRedirects(self.log_in(next=destination), destination)

    def test_login_rejects_external_next_destinations(self):
        for destination in ['https://example.com/', '//example.com/']:
            with self.subTest(destination=destination):
                self.client.logout()
                self.assertRedirects(self.log_in(next=destination), reverse('home'))

    def test_authenticated_user_is_redirected_away_from_login(self):
        self.client.force_login(self.user)

        self.assertRedirects(self.client.get(reverse('login')), reverse('home'))

    def test_post_logout_clears_session(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('logout'))

        self.assertRedirects(response, reverse('home'))
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertContains(self.client.get(reverse('home')), 'Create account')

    def test_get_logout_is_rejected_without_ending_session(self):
        self.client.force_login(self.user)

        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertIn(SESSION_KEY, self.client.session)


class CsrfTests(TestCase):
    def test_account_endpoints_reject_posts_without_csrf_tokens(self):
        for route in ['register', 'login', 'logout']:
            with self.subTest(route=route):
                client = Client(enforce_csrf_checks=True)
                self.assertEqual(client.post(reverse(route)).status_code, 403)
        self.assertFalse(User.objects.exists())

    def test_register_login_logout_flow_with_csrf_protection(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse('register'))
        response = client.post(reverse('register'), {
            'username': 'csrf_player',
            'password1': TEST_PASSWORD,
            'password2': TEST_PASSWORD,
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
        })
        self.assertRedirects(response, reverse('login'))

        response = client.post(reverse('login'), {
            'username': 'csrf_player',
            'password': TEST_PASSWORD,
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
        })
        self.assertRedirects(response, reverse('home'))
        self.assertIn(SESSION_KEY, client.session)

        # Logging in rotates the CSRF token; use the one from the member page.
        home = client.get(reverse('home'))
        self.assertContains(home, 'action="' + reverse('logout') + '"')
        self.assertEqual(client.post(reverse('logout')).status_code, 403)
        self.assertIn(SESSION_KEY, client.session)
        response = client.post(reverse('logout'), {
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
        })
        self.assertRedirects(response, reverse('home'))
        self.assertNotIn(SESSION_KEY, client.session)