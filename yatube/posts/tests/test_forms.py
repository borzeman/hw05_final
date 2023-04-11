import shutil
import tempfile

from django.test import Client, override_settings, TestCase
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from posts.models import Post, Group, Comment, User


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
POSTNUM_1 = 1


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.group = Group.objects.create(
            title='группа',
            slug='slug',
            description='описание1'
        )
        cls.group2 = Group.objects.create(
            title='группа2',
            slug='group2_slug',
            description='описание2'
        )
        cls.create_post = Post.objects.create(
            text='текст поста',
            author=cls.user,
            group=cls.group
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post_text_form = {'text': 'Измененный тект',
                              'group': cls.group.pk,
                              'image': uploaded,
                              }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_edit(self):
        """При изменении валидной формы изменяется запись в базе данных."""
        self.post_without_group = Post.objects.create(
            text='текст поста без группы',
            author=self.user
        )
        self.post = Post.objects.create(
            text='Тестовый текст',
            author=self.user,
            group=self.group
        )
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Новый текст поста',
            'group': self.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}),
        )
        self.assertEqual(Post.objects.count(), posts_count)
        post = Post.objects.get(id=self.post.id)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.id, form_data['group'])

    def test_edit_other_users_post(self):
        """При попытке изменить пост другого пользователя, пост не меняется."""
        user1 = User.objects.create_user(username='user1')
        user2 = User.objects.create_user(username='user2')
        client1 = Client()
        client1.force_login(user1)
        post = Post.objects.create(
            text='Тестовый текст',
            author=user1,
            group=self.group,
        )
        client2 = Client()
        client2.force_login(user2)
        form_data = {
            'text': 'Новый текст поста',
            'group': self.group.id,
        }
        client2.post(reverse('posts:post_edit', kwargs={'post_id': post.id}))
        post.refresh_from_db()
        self.assertEqual(post.text, 'Тестовый текст')
        self.assertEqual(post.author, user1)
        self.assertNotEqual(post.text, form_data['text'])

    def test_create_post_user(self):
        """Тест работы формы зарегистрированного юзера"""
        id_set_original = set(Post.objects.values_list('id', flat=True))
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=self.post_text_form,
            follow=True
        )
        id_set_modify = set(Post.objects.values_list('id', flat=True))

        self.assertEqual(len([id_set_modify]), POSTNUM_1)
        id_post = list(set(id_set_modify) - set(id_set_original))[0]
        post = Post.objects.get(pk=id_post)
        self.assertEqual(self.post_text_form['text'], post.text)
        self.assertEqual(self.post_text_form['group'], post.group.pk)
        self.assertEqual(f'posts/{self.post_text_form["image"]}', post.image)
        self.assertEqual(self.user, post.author)
        self.assertEqual(response.status_code, 200)

    def test_unauth_user(self):
        """"Тест работы формы для юзера без авторизации"""
        posts_count = Post.objects.count()
        text_form = {'text': 'текст'}
        response = self.client.post(
            reverse('posts:post_create'),
            data=text_form,
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), posts_count)

    def test_author_edit(self):
        """Корректировка поста авторизованным юзером"""
        text_form = {'text': 'Новый текст',
                     'group': self.group2.pk}
        author_response = self.authorized_client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.create_post.id}),
            data=text_form
        )
        edit_post = Post.objects.select_related(
            'group', 'author').get(pk=self.create_post.id)
        self.assertEqual(author_response.status_code, 302)
        self.assertEqual(edit_post.author, self.create_post.author)
        self.assertEqual(edit_post.text, text_form['text'])
        self.assertEqual(edit_post.group.pk, self.group2.pk)

    def test_unauth_user_edit(self):
        """Корректировка поста неавторизованным юзером"""
        guest_response = self.client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.create_post.id}),
            data=self.post_text_form)
        edit_post = Post.objects.select_related(
            'group', 'author').get(pk=self.create_post.id)
        self.assertEqual(guest_response.status_code, 302)
        self.assertEqual(edit_post.author, self.create_post.author)
        self.assertEqual(edit_post.text, 'текст поста')
        self.assertEqual(edit_post.group.pk, self.group.pk)

    def test_auth_user_add_comment(self):
        """Корректировка комментария авторизованным юзером"""
        form = {'text': 'hola'}
        old_comments_count = Comment.objects.count()
        self.authorized_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': self.create_post.id}),
            data=form
        )
        new_comments_count = Comment.objects.count()
        self.assertEqual(new_comments_count, old_comments_count + 1)
        latest_comment = Comment.objects.latest('pk')
        self.assertEqual(latest_comment.post, self.create_post)
        self.assertEqual(latest_comment.author, self.create_post.author)
        self.assertEqual(latest_comment.text, form['text'])

    def test_unauth_user_edit(self):
        """Корректировка комментария неавторизованным юзером"""
        form = {'text': 'hola'}
        original_comment_num = Comment.objects.count()
        self.client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': self.create_post.id}),
            data=form)
        changed_comment_num = Comment.objects.count()
        self.assertEqual(changed_comment_num, original_comment_num)
