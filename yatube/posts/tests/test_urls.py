from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from posts.models import Post, Group

SUCCESS_STATUS_CODE = 200
STATUS_CODE_404 = 404
STATUS_CODE_302 = 302

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Author')
        cls.user = User.objects.create_user(username='NonAuthor')
        cls.post = Post.objects.create(
            text='чонитьтам',
            author=cls.author
        )
        cls.group = Group.objects.create(
            title='Группа',
            slug='test_slug',
            description='описание'
        )

    def setUp(self):
        self.authorized_client = Client()
        self.auth_client = Client()
        self.authorized_client.force_login(self.user)
        self.auth_client.force_login(self.author)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.author.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/posts/{self.post.id}/edit/': 'posts/post_create.html',
            '/create/': 'posts/post_create.html',
            '/about/tech/': 'about/tech.html',
            '/about/author/': 'about/author.html'
        }

        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.auth_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_url_exists_at_desired_location(self):
        """Страницы доступны любому авторизованному пользователю"""
        urls = {
            '/': SUCCESS_STATUS_CODE,
            f'/group/{self.group.slug}/': SUCCESS_STATUS_CODE,
            f'/profile/{self.author.username}/': SUCCESS_STATUS_CODE,
            f'/posts/{self.post.id}/': SUCCESS_STATUS_CODE,
            '/create/': SUCCESS_STATUS_CODE,
        }
        for url, status_code in urls.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, status_code)

    def test_edit_url_location(self):
        """Страница редактирования доступна автору поста."""
        response = self.auth_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, SUCCESS_STATUS_CODE)

    def test_create_url_guest(self):
        """Страница создания поста недоступна гостю"""
        response = self.client.get('/create/')
        self.assertEqual(response.status_code, STATUS_CODE_302)

    def test_edit_url_guest(self):
        """Страница редактирования поста недоступна гостю"""
        response = self.client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, STATUS_CODE_302)

    def test_edit_url_not_author(self):
        """Страница редактирования недоступна неавтору"""
        response = self.authorized_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, STATUS_CODE_302)

    def test_404(self):
        """Страница недоступна"""
        response = self.client.get('/404/')
        self.assertEqual(response.status_code, STATUS_CODE_404)
