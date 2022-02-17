from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Comment, Group, Post


User = get_user_model()


class ModelTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый очень сильно много офигенно дофига длинный пост',
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый очень сильно длинный многословный комментарий'
        )

    def test_post_have_correct_object_name(self):
        """Проверяем, что у модели Post корректно работает __str__."""
        expected_object_name = ModelTests.post.text[:15]
        self.assertEqual(expected_object_name, str(ModelTests.post))

    def test_group_have_correct_object_name(self):
        """Проверяем, что у модели Group корректно работает __str__."""
        expected_object_name = ModelTests.group.title
        self.assertEqual(expected_object_name, str(ModelTests.group))

    def test_comment_have_correct_object_name(self):
        """Проверяем, что у модели Comment корректно работает __str__."""
        expected_object_name = ModelTests.comment.text[:15]
        self.assertEqual(expected_object_name, str(ModelTests.comment))
