import os
import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class FormTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='new_user')
        cls.another_user = User.objects.create_user(
            username='new_another_user'
        )
        cls.groups = []
        for i in range(1, 4):
            group = Group.objects.create(
                title=f'group {i}',
                description='test group',
                slug=f'group{i}-slug'
            )
            cls.groups.append(group)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(FormTests.user)
        self.another_authorized_client = Client()
        self.another_authorized_client.force_login(FormTests.another_user)
        self.post = Post.objects.create(
            author=FormTests.user,
            text='Тестовый пост',
        )

    def test_create_post(self):
        """Валидная форма создаёт новый пост."""
        posts_count = Post.objects.count()
        post_text = 'Новый тестовый пост, созданный пользователем'
        post_group = FormTests.groups[0]
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        post_image = SimpleUploadedFile(
            name='test_image.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': post_text,
            'group': post_group.id,
            'image': post_image,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', args=[FormTests.user.username])
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        new_post = Post.objects.all().order_by('-id')[0]
        self.assertEqual(new_post.text, post_text)
        self.assertEqual(new_post.group, post_group)
        # У картинки new_post.image в name будет полный путь до файла,
        # а у ранее созданного файла в name будет только имя файла.
        # Поэтому у new_post.image.name нужно явно отделить имя файла
        # и использовать его при сравнении
        self.assertEqual(
            os.path.split(new_post.image.name)[1],
            post_image.name
        )

    def test_edit_post(self):
        """При отправке валидной формы редактирования пост изменяется."""
        posts_count = Post.objects.count()
        post_text = 'Пост, отредактированный пользователем'
        post_group = FormTests.groups[1]
        form_data = {
            'text': post_text,
            'group': post_group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=[self.post.id]),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=[self.post.id])
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.post.refresh_from_db()
        self.assertEqual(self.post.text, post_text)
        self.assertEqual(self.post.group, post_group)

    def test_add_comment(self):
        """Валидная форма добавляет комментарий к посту."""
        comments_count = Comment.objects.count()
        comment_text = 'Тестовый комментарий'
        form_data = {
            'text': comment_text
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=[self.post.id]),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=[self.post.id])
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        new_comment = Comment.objects.all().order_by('-id')[0]
        self.assertEqual(new_comment.text, comment_text)
        self.assertEqual(new_comment.post, self.post)

    def test_create_post_by_anonymous_user(self):
        """Анонимный пользователь не может создать пост"""
        posts_count = Post.objects.count()
        post_text = 'Пост, созданный анонимом'
        form_data = {
            'text': post_text,
        }
        post_create_url = reverse('posts:post_create')
        response = self.client.post(
            post_create_url,
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            f'{reverse("users:login")}?next={post_create_url}'
        )
        self.assertEqual(Post.objects.count(), posts_count)

    def test_edit_post_by_anonymous_user(self):
        """При отправке валидной формы редактирования анонимным пользователем
        пост не изменяется.
        """
        posts_count = Post.objects.count()
        post_text = 'Пост, отредактированный анонимом'
        post_group = FormTests.groups[2]
        form_data = {
            'text': post_text,
            'group': post_group.id,
        }
        post_edit_url = reverse('posts:post_edit', args=[self.post.id])
        response = self.client.post(
            post_edit_url,
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            f'{reverse("users:login")}?next={post_edit_url}'
        )
        self.assertEqual(Post.objects.count(), posts_count)
        old_text = self.post.text
        old_group = self.post.group
        self.post.refresh_from_db()
        new_text = self.post.text
        new_group = self.post.group
        self.assertEqual(old_text, new_text)
        self.assertEqual(old_group, new_group)

    def test_edit_post_by_not_author(self):
        """При отправке валидной формы редактирования не автором
        пост не изменяется.
        """
        posts_count = Post.objects.count()
        post_text = 'Пост, отредактированный не автором'
        form_data = {
            'text': post_text,
        }
        post_edit_url = reverse('posts:post_edit', args=[self.post.id])
        response = self.another_authorized_client.post(
            post_edit_url,
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=[self.post.id]),
        )
        self.assertEqual(Post.objects.count(), posts_count)
        old_text = self.post.text
        self.post.refresh_from_db()
        new_text = self.post.text
        self.assertEqual(old_text, new_text)

    def test_add_comment_by_anonymous_user(self):
        """Анонимный пользователь не может комментировать пост"""
        comments_count = Comment.objects.count()
        comment_text = 'Комментарий, созданный анонимом'
        form_data = {
            'text': comment_text,
        }
        add_comment_url = reverse('posts:add_comment', args=[self.post.id])
        response = self.client.post(
            add_comment_url,
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            f'{reverse("users:login")}?next={add_comment_url}'
        )
        self.assertEqual(Comment.objects.count(), comments_count)
