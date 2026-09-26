"""HTTP-level regression tests for optional Resource layers."""
from unittest.mock import Mock

from django.contrib.auth.models import AnonymousUser, User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase

from .models import Article
from .resources import ArticleResource


class LayerTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="layers")
        self.resource = ArticleResource()

    def request(self, method="get", data=None, user=None, **headers):
        request = getattr(self.factory, method)("/articles/", data or {}, **headers)
        request.user = self.user if user is None else user
        request.session = {}
        request._messages = FallbackStorage(request)
        return request


class SignalTests(LayerTestCase):
    def setUp(self):
        super().setUp()
        from djresource.signals import (
            resource_pre_save, resource_post_save, resource_post_delete,
        )
        self.events = []
        for name, signal in [("pre", resource_pre_save), ("post", resource_post_save),
                             ("delete", resource_post_delete)]:
            def receiver(sender, instance, resource, name=name, **kwargs):
                self.assertIs(sender, Article)
                self.assertIs(resource, self.resource)
                self.events.append((name, instance.pk))
            signal.connect(receiver, sender=Article, weak=False)
            self.addCleanup(signal.disconnect, receiver, sender=Article)

    def test_signals_complement_hooks_on_create_update_delete(self):
        self.resource.before_save = lambda *a: self.events.append(("before", None))
        self.resource.after_save = lambda obj, *a: self.events.append(("after", obj.pk))
        response = self.resource.get_create_view().as_view()(
            self.request("post", {"titre": "A", "slug": "a"})
        )
        self.assertEqual(response.status_code, 302)
        obj = Article.objects.get()
        self.assertEqual(self.events, [("before", None), ("pre", None),
                                       ("after", obj.pk), ("post", obj.pk)])
        self.events.clear()
        self.resource.get_update_view().as_view()(
            self.request("post", {"titre": "B", "slug": "a"}), slug="a"
        )
        self.assertEqual([x[0] for x in self.events], ["before", "pre", "after", "post"])
        self.events.clear()
        self.resource.after_delete = lambda *a: self.events.append(("after_delete", None))
        self.resource.get_delete_view().as_view()(self.request("post"), slug="a")
        self.assertEqual(self.events, [("after_delete", None), ("delete", None)])

    def test_veto_emits_no_signal(self):
        self.resource.clean = Mock(side_effect=ValidationError("No"))
        self.resource.get_create_view().as_view()(
            self.request("post", {"titre": "A", "slug": "a"})
        )
        self.assertEqual(self.events, [])
        Article.objects.create(titre="A", slug="a")
        self.resource.before_delete = Mock(side_effect=ValidationError("No"))
        self.resource.get_delete_view().as_view()(self.request("post"), slug="a")
        self.assertEqual(self.events, [])
