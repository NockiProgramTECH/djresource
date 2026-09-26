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


class HTMXTests(LayerTestCase):
    def test_templates_for_all_views_and_themes(self):
        Article.objects.create(titre="A", slug="a")
        for theme in ("bootstrap", "tailwind", "plain"):
            self.resource.theme = theme
            for action, kind in (("list", "list"), ("create", "form"),
                                 ("update", "form"), ("delete", "confirm_delete"),
                                 ("detail", "detail")):
                for enabled, header in ((False, "true"), (True, "false"), (True, "true")):
                    with self.subTest(theme=theme, action=action, enabled=enabled, header=header):
                        self.resource.htmx = enabled
                        kwargs = {"slug": "a"} if action in ("update", "delete", "detail") else {}
                        response = getattr(self.resource, f"get_{action}_view")().as_view()(
                            self.request(HTTP_HX_REQUEST=header), **kwargs
                        )
                        partial = enabled and header == "true"
                        self.assertEqual(response.template_name[0], self.resource._theme_template(
                            kind + ("_partial" if partial else ""), None))
                        response.render()
                        self.assertEqual(b"<!doctype html>" in response.content.lower(), not partial)
                        if enabled:
                            self.assertIn("HX-Request", response["Vary"])

    def test_invalid_post_is_partial_success_still_redirects(self):
        self.resource.htmx = True
        view = self.resource.get_create_view().as_view()
        response = view(self.request("post", {}, HTTP_HX_REQUEST="true"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, ["djresource/tailwind/form_partial.html"])
        response = view(self.request("post", {"titre": "A", "slug": "a"}, HTTP_HX_REQUEST="true"))
        self.assertEqual(response.status_code, 302)

    def test_htmx_does_not_bypass_authentication(self):
        from .resources import ArticleDefaultProtectedResource
        resource = ArticleDefaultProtectedResource()
        resource.htmx = True
        response = resource.get_list_view().as_view()(
            self.request(user=AnonymousUser(), HTTP_HX_REQUEST="true")
        )
        self.assertEqual(response.status_code, 302)
