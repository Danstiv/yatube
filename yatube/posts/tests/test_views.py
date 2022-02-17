import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms

from ..models import Post, Group

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ViewTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='new_user')
        cls.users = [
            User.objects.create_user(username='user1'),
            User.objects.create_user(username='user2')
        ]
        cls.group1 = Group.objects.create(
            title='Тестовая группа1',
            slug='test-slug1',
            description='Тестовое описание',
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='Тестовое описание',
        )
        for i in range(1, 16):  # Create 15 posts
            Post.objects.create(
                author=cls.user,
                text=f'Тестовый пост {i}',
            )
        cls.posts = list(Post.objects.all())
        cls.posts[0].group = cls.group1
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        image = SimpleUploadedFile(
            name='test_image.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.posts[0].image = image
        cls.posts[0].save()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.client.force_login(ViewTests.user)
        self.clients = []
        for user in ViewTests.users:
            client = Client()
            client.force_login(user)
            self.clients.append(client)

    def test_correct_templates_used(self):
        """view использует правильный шаблон"""
        urls_template_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                args=[ViewTests.group1.slug]
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                args=[ViewTests.user.username]
            ): 'posts/profile.html',
            reverse(
                'posts:post_edit',
                args=[ViewTests.posts[0].id]
            ): 'posts/create_post.html',
            reverse(
                'posts:post_detail',
                args=[ViewTests.posts[0].id]
            ): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for url, template in urls_template_names.items():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertTemplateUsed(response, template)

    def test_index_and_profile_pages_have_correct_context(self):
        """Шаблон главной страницы и страницы профиля имеет верный контекст"""
        urls_list = [
            reverse('posts:index'),
            reverse('posts:profile', args=[ViewTests.user.username]),
        ]
        for url in urls_list:
            with self.subTest(url=url):
                response = self.client.get(url)
                page_obj = response.context['page_obj']
                post = page_obj[0]
                self.assertEqual(ViewTests.posts[0].id, post.id)
                self.assertTrue(post.image)
                self.assertEqual(ViewTests.posts[0].image, post.image)
                self.assertEqual(len(page_obj), settings.POSTS_PER_PAGE)

    def test_group_page_have_correct_context(self):
        """Шаблон группы имеет верный контекст"""
        response = self.client.get(
            reverse('posts:group_list', args=[ViewTests.group1.slug])
        )
        page_obj = response.context['page_obj']
        post = page_obj[0]
        self.assertEqual(ViewTests.posts[0].id, post.id)
        self.assertTrue(post.image)
        self.assertEqual(ViewTests.posts[0].image, post.image)
        self.assertEqual(len(page_obj), 1)

    def test_post_pages_have_correct_context(self):
        """Шаблоны создания, редактирования
        и просмотра поста имеют верный контекст
        """
        post = ViewTests.posts[5]
        urls_list = [
            reverse('posts:post_detail', args=[post.id]),
            reverse('posts:post_edit', args=[post.id]),
        ]
        for url in urls_list:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.context['post'], post)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        urls_list = [
            reverse('posts:post_create'),
            reverse('posts:post_edit', args=[post.id]),
        ]
        for url in urls_list:
            with self.subTest(url=url):
                response = self.client.get(url)
                form = response.context['form']
                for field_name, field_type in form_fields.items():
                    with self.subTest(field_name=field_name):
                        field = form.fields[field_name]
                        self.assertIsInstance(field, field_type)

    def test_post_detail_page_have_image(self):
        """На странице поста есть его картинка"""
        response = self.client.get(
            reverse('posts:post_detail', args=[ViewTests.posts[0].id])
        )
        post = response.context['post']
        self.assertTrue(post.image)
        self.assertEqual(ViewTests.posts[0].image, post.image)

    def test_post_in_group_displayed_correctly(self):
        """Пост, добавленный в группу,
        выводется на главную страницу,
        на страницу пользователя,
        на страницу группы
        и не выводится на страницу другой группы"""
        post_with_group = ViewTests.posts[0]
        self.assertEqual(post_with_group.group, self.group1)
        urls_list = [
            reverse('posts:index'),
            reverse('posts:profile', args=[ViewTests.user.username]),
            reverse('posts:group_list', args=[ViewTests.group1.slug]),
        ]
        for url in urls_list:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertIn(post_with_group, response.context['page_obj'])
        response = self.client.get(
            reverse('posts:group_list', args=[ViewTests.group2.slug])
        )
        self.assertNotIn(post_with_group, response.context['page_obj'])

    def test_posts_cached_on_index_page(self):
        """Посты на главной странице кешируются"""
        # Если этот тест упадёт, при использовании assertEqual
        # будет очень много вывода.
        # Поэтому используется assertTrue и assertFalse.
        cache.clear()
        response = self.client.get(reverse('posts:index'))
        # Кеш был очищен, выполненный после очистки запрос сгенерировал новый
        initial_content = response.content
        # Этот пост точно отображается на странице,
        # его удаление должно привести к изменению страницы
        # после истечения срока хранения кеша.
        post = Post.objects.all()[0]
        post.delete()
        response = self.client.get(reverse('posts:index'))
        # Так как посты кешируются, данные не должны отличаться
        self.assertTrue(response.content == initial_content)
        cache.delete(make_template_fragment_key('index_page'))
        response = self.client.get(reverse('posts:index'))
        # Теперь данные должны отличаться от изначальных,
        # Потому что пост был изменён,
        # И кеш, содержащий старые посты, удалён.
        self.assertFalse(response.content == initial_content)

    def test_authorized_user_can_follow_other_user(self):
        """Авторизованный пользователь может подписываться
        На других пользователей
        и отписываться от них."""
        user_url = ViewTests.users[0].get_absolute_url()
        # Изначально пользователь должен быть отписан
        response = self.client.get(user_url)
        self.assertFalse(response.context['following'])
        response = self.client.get(
            reverse(
                'posts:profile_follow',
                args=[ViewTests.users[0].username]
            ),
            follow=True
        )
        self.assertRedirects(response, user_url)
        self.assertTrue(response.context['following'])
        response = self.client.get(
            reverse(
                'posts:profile_unfollow',
                args=[ViewTests.users[0].username]
            ),
            follow=True
        )
        self.assertRedirects(response, user_url)
        self.assertFalse(response.context['following'])

    def test_post_appears_in_feed(self):
        """Пост появляется в ленте у пользователей,
        которые потписаны на автора поста,
        и не появляется у тех,
        кто на автора не подписан"""
        response = self.clients[0].get(
            reverse(
                'posts:profile_follow',
                args=[ViewTests.user.username]
            ),
            follow=True
        )
        new_post = Post.objects.create(author=ViewTests.user, text='post text')
        response = self.clients[0].get(reverse('posts:follow_index'))
        self.assertIn(new_post, response.context['page_obj'])
        response = self.clients[1].get(reverse('posts:follow_index'))
        self.assertNotIn(new_post, response.context['page_obj'])
