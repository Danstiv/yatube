from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from ..models import Post, Group

User = get_user_model()


class URLTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(URLTests.user)

    def test_urls_exists_and_uses_correct_template(self):
        """URL-адрес существует и использует соответствующий шаблон."""
        urls_template_names = {
            '/': 'posts/index.html',
            f'/group/{URLTests.group.slug}/': 'posts/group_list.html',
            f'/profile/{URLTests.user.username}/': 'posts/profile.html',
            f'/posts/{URLTests.post.id}/edit/': 'posts/create_post.html',
            f'/posts/{URLTests.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
        }
        for url, template in urls_template_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(
                    response.status_code,
                    200,
                    f'URL {url}: код {response.status_code}'
                )
                self.assertTemplateUsed(response, template)

    def test_private_url_redirects(self):
        """Запросы на адреса, доступные только авторизованным пользователям,
        перенаправляются на страницу авторизации
        """
        url_list = [
            f'/posts/{URLTests.post.id}/edit/',
            '/create/',
        ]
        for url in url_list:
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertRedirects(response, f'/auth/login/?next={url}')

    def test_non_existent_urls(self):
        """Запросы, в ответ на которые должен возвращаться ответ с кодом 404"""
        url_list = [
            '/group/123123123/',
            '/profile/abc12345/',
            '/posts/4044224404/edit/',
            '/posts/404404404404/',
        ]
        for url in url_list:
            with self.subTest(url=url):
                response = self.authorized_client.get(url, follow=True)
                self.assertEqual(response.status_code, 404)
                self.assertTemplateUsed(response, 'core/404.html')
