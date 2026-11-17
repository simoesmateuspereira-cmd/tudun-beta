from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice

from .models import Comment, Community, Membership, Post


class FeedViewsTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user("admin-mural", "admin.mural@example.invalid", "Senha-Ficticia-123")
        self.member = User.objects.create_user("membro-mural", "membro.mural@example.invalid", "Senha-Ficticia-123")
        self.other_member = User.objects.create_user("outro-mural", "outro.mural@example.invalid", "Senha-Ficticia-123")
        self.outsider = User.objects.create_user("externo-mural", "externo.mural@example.invalid", "Senha-Ficticia-123")
        self.community = Community.objects.create(name="Comunidade Mural", slug="mural-teste", created_by=self.admin)
        for user, role in ((self.admin, Membership.Role.ADMIN), (self.member, Membership.Role.MEMBER), (self.other_member, Membership.Role.MEMBER)):
            Membership.objects.create(
                community=self.community,
                user=user,
                role=role,
                status=Membership.Status.ACTIVE,
                joined_at=timezone.now(),
            )

    def test_member_can_create_post(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("communities:post_create", kwargs={"slug": self.community.slug}),
            {"body": "Consegui minha primeira conquista na comunidade!"},
        )
        self.assertEqual(response.status_code, 302)
        post = Post.objects.get()
        self.assertEqual(post.author, self.member)
        self.assertEqual(post.community, self.community)

    def test_outsider_cannot_create_post(self):
        self.client.force_login(self.outsider)
        response = self.client.post(
            reverse("communities:post_create", kwargs={"slug": self.community.slug}),
            {"body": "Post de fora"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Post.objects.count(), 0)

    def test_feed_requires_membership(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("communities:feed", kwargs={"slug": self.community.slug}))
        self.assertEqual(response.status_code, 403)

    def test_member_sees_feed_and_post(self):
        post = Post.objects.create(community=self.community, author=self.member, body="Experiência incrível!")
        self.client.force_login(self.member)
        response = self.client.get(reverse("communities:feed", kwargs={"slug": self.community.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Experiência incrível!")

    def test_like_toggle(self):
        post = Post.objects.create(community=self.community, author=self.member, body="Post curtível")
        url = reverse("communities:post_like", kwargs={"slug": self.community.slug, "post_id": post.pk})
        self.client.force_login(self.other_member)
        self.client.post(url)
        self.assertTrue(post.likes.filter(pk=self.other_member.pk).exists())
        self.client.post(url)
        self.assertFalse(post.likes.filter(pk=self.other_member.pk).exists())

    def test_comment_add(self):
        post = Post.objects.create(community=self.community, author=self.member, body="Post comentável")
        self.client.force_login(self.other_member)
        self.client.post(
            reverse("communities:comment_create", kwargs={"slug": self.community.slug, "post_id": post.pk}),
            {"body": "Parabéns pela conquista!"},
        )
        comment = Comment.objects.get(post=post)
        self.assertEqual(comment.author, self.other_member)
        self.assertEqual(comment.body, "Parabéns pela conquista!")

    def test_author_can_delete_own_post(self):
        post = Post.objects.create(community=self.community, author=self.member, body="Vou apagar")
        self.client.force_login(self.member)
        self.client.post(reverse("communities:post_delete", kwargs={"slug": self.community.slug, "post_id": post.pk}))
        self.assertEqual(Post.objects.count(), 0)

    def test_other_member_cannot_delete_post(self):
        post = Post.objects.create(community=self.community, author=self.member, body="Não pode apagar")
        self.client.force_login(self.other_member)
        self.client.post(reverse("communities:post_delete", kwargs={"slug": self.community.slug, "post_id": post.pk}))
        self.assertEqual(Post.objects.count(), 1)

    def verified_login(self, user):
        self.client.force_login(user)
        device = TOTPDevice.objects.create(user=user, name="Teste", confirmed=True)
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        session.save()

    def test_admin_can_delete_any_post(self):
        post = Post.objects.create(community=self.community, author=self.member, body="Moderação")
        self.verified_login(self.admin)
        self.client.post(reverse("communities:post_delete", kwargs={"slug": self.community.slug, "post_id": post.pk}))
        self.assertEqual(Post.objects.count(), 0)
