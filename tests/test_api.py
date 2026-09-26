"""Optional DRF integration and dependency-isolation regression tests."""
import os
import subprocess
import sys
from unittest import skipUnless
from unittest.mock import Mock

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase

from djresource.resource import Resource
from .models import Article
from .resources import (
    ArticleBusinessProtectedResource, ArticleDefaultProtectedResource,
    ArticleResource, ArticleScopedResource,
)

try:
    from rest_framework.test import APIRequestFactory, force_authenticate
except ImportError:
    APIRequestFactory = None


class OptionalAPITests(TestCase):
    def test_core_and_html_work_with_drf_imports_blocked(self):
        # A fresh interpreter also proves core does not eagerly import api/DRF.
        code = '''
import builtins
original_import = builtins.__import__
def blocked(name, *args, **kwargs):
    if name == "rest_framework" or name.startswith("rest_framework."):
        raise ImportError("DRF deliberately unavailable")
    return original_import(name, *args, **kwargs)
builtins.__import__ = blocked
import django
django.setup()
import sys
from tests.resources import ArticleResource
assert "djresource.api" not in sys.modules
assert not any(m.startswith("rest_framework") for m in sys.modules)
resource = ArticleResource()
resource.get_list_view()
resource.get_create_view()
from django.core.exceptions import ImproperlyConfigured
try:
    resource.as_viewset()
except ImproperlyConfigured as exc:
    assert "djresource[api]" in str(exc)
else:
    raise AssertionError("Missing DRF must fail explicitly")
'''
        result = subprocess.run([sys.executable, "-c", code], env=os.environ.copy(),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


@skipUnless(APIRequestFactory, "Optional Django REST Framework is not installed")
class APITests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username="api-owner")
        self.other = User.objects.create_user(username="other")
        self.resource = ArticleScopedResource()
        # Scoped resources still need authentication, including on create.
        self.resource.public = False
        self.article = Article.objects.create(titre="Owned", slug="owned", owner=self.user)
        self.foreign = Article.objects.create(titre="Foreign", slug="foreign", owner=self.other)

    def call(self, action="list", method="get", data=None, resource=None, user=True, **kwargs):
        request = getattr(self.factory, method)("/api/articles/", data or {}, format="json")
        if user is not None:
            force_authenticate(request, user=self.user if user is True else user)
        cls = (resource or self.resource).as_viewset()
        return cls.as_view({method: action})(request, **kwargs)

    def test_default_authentication_and_public_opt_out(self):
        self.assertIn(self.call(resource=ArticleDefaultProtectedResource(), user=None).status_code, (401, 403))
        response = self.call(resource=ArticleResource(), user=None)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_business_permissions_and_explicit_mixins(self):
        resource = ArticleBusinessProtectedResource()
        self.assertEqual(self.call(resource=resource).status_code, 403)
        allowed = User.objects.create_user(username="allowed")
        self.assertEqual(self.call(resource=resource, user=allowed).status_code, 200)

        from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
        resource.get_permissions = lambda: [LoginRequiredMixin, PermissionRequiredMixin]
        resource.permission_required = "tests.change_article"
        self.user.has_perms = Mock(return_value=False)
        self.assertEqual(self.call(resource=resource).status_code, 403)
        self.user.has_perms = Mock(return_value=True)
        self.assertEqual(self.call(resource=resource).status_code, 200)
        self.user.has_perms.assert_called_with(("tests.change_article",))

    def test_custom_permission_response_fails_closed(self):
        from django.http import HttpResponse, HttpResponseForbidden

        class Deny:
            def dispatch(self, request, *args, **kwargs):
                return HttpResponseForbidden()

        self.resource.get_permissions = lambda: [Deny]
        self.assertEqual(self.call().status_code, 403)

        class DoesNotDelegate:
            def dispatch(self, request, *args, **kwargs):
                return HttpResponse("not permission approval")

        self.resource.get_permissions = lambda: [DoesNotDelegate]
        self.assertEqual(self.call().status_code, 403)

    def test_scope_applies_to_all_reads_and_writes(self):
        response = self.call()
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["slug"] for row in response.data["results"]], ["owned"])
        for action, method in (("retrieve", "get"), ("partial_update", "patch"), ("destroy", "delete")):
            with self.subTest(action=action):
                self.assertEqual(self.call(action, method, slug="foreign").status_code, 404)
        self.assertTrue(Article.objects.filter(pk=self.foreign.pk).exists())
        self.assertEqual(self.call("retrieve", slug="owned").status_code, 200)

    def test_create_assigns_owner_and_calls_hooks_and_signals(self):
        from djresource.signals import resource_pre_save, resource_post_save
        pre, post = Mock(), Mock()
        resource_pre_save.connect(pre, sender=Article, weak=False)
        resource_post_save.connect(post, sender=Article, weak=False)
        self.addCleanup(resource_pre_save.disconnect, pre, sender=Article)
        self.addCleanup(resource_post_save.disconnect, post, sender=Article)
        self.resource.after_save = Mock()
        response = self.call("create", "post", {"titre": "New", "slug": "new", "owner": self.other.pk})
        self.assertEqual(response.status_code, 201)
        instance = Article.objects.get(slug="new")
        self.assertEqual(instance.owner, self.user)
        self.resource.after_save.assert_called_once()
        self.assertTrue(self.resource.after_save.call_args.args[2])
        for receiver in (pre, post):
            receiver.assert_called_once()
            self.assertIs(receiver.call_args.kwargs["sender"], Article)
            self.assertIs(receiver.call_args.kwargs["resource"], self.resource)
        self.assertEqual(post.call_args.kwargs["instance"].pk, instance.pk)

    def test_update_preserves_readonly_fields_and_calls_hooks(self):
        self.resource.readonly_fields = ["slug"]
        self.resource.after_save = Mock()
        response = self.call("partial_update", "patch", {"titre": "Updated", "slug": "hacked"}, slug="owned")
        self.assertEqual(response.status_code, 200)
        self.article.refresh_from_db()
        self.assertEqual(self.article.titre, "Updated")
        self.assertEqual(self.article.slug, "owned")
        self.assertFalse(self.resource.after_save.call_args.args[2])

    def test_validation_veto_does_not_write(self):
        self.resource.clean = Mock(side_effect=ValidationError({"titre": "Refused"}))
        response = self.call("create", "post", {"titre": "New", "slug": "new"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("titre", response.data)
        self.assertFalse(Article.objects.filter(slug="new").exists())
        response = self.call("partial_update", "patch", {"titre": "No"}, slug="owned")
        self.assertEqual(response.status_code, 400)
        self.article.refresh_from_db()
        self.assertEqual(self.article.titre, "Owned")

    def test_after_save_failure_rolls_back(self):
        self.resource.after_save = Mock(side_effect=ValidationError("Late failure"))
        response = self.call("create", "post", {"titre": "New", "slug": "new"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Article.objects.filter(slug="new").exists())

    def test_delete_hooks_veto_and_success_signal(self):
        from djresource.signals import resource_post_delete
        receiver = Mock()
        resource_post_delete.connect(receiver, sender=Article, weak=False)
        self.addCleanup(resource_post_delete.disconnect, receiver, sender=Article)
        self.resource.before_delete = Mock(side_effect=ValidationError("Keep"))
        self.resource.after_delete = Mock()
        self.assertEqual(self.call("destroy", "delete", slug="owned").status_code, 400)
        self.assertTrue(Article.objects.filter(pk=self.article.pk).exists())
        self.resource.after_delete.assert_not_called()
        receiver.assert_not_called()
        self.resource.before_delete = Mock()
        self.assertEqual(self.call("destroy", "delete", slug="owned").status_code, 204)
        self.resource.after_delete.assert_called_once()
        receiver.assert_called_once()
        self.assertIsNone(receiver.call_args.kwargs["instance"].pk)

    def test_search_ordering_filter_and_pagination(self):
        Article.objects.create(titre="Owned Z", slug="owned-z", owner=self.user)
        Article.objects.create(titre="Owned inactive", slug="inactive", owner=self.user, actif=False)
        self.resource.search_fields = ["titre"]
        self.resource.ordering_fields = ["titre"]
        self.resource.paginate_by = 1
        params = {"search": "Owned", "ordering": "-titre", "actif": "true"}
        response = self.call(data=params)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"][0]["slug"], "owned-z")
        response = self.call(data={**params, "page": "2"})
        self.assertEqual(response.data["results"][0]["slug"], "owned")
        response = self.call(data={"ordering": "-slug", "actif": "true"})
        self.assertEqual(response.data["results"][0]["slug"], "owned")  # model default titre order

    def test_serializer_only_exposes_declared_fields(self):
        serializer = self.resource.as_viewset().serializer_class()
        self.assertEqual(set(serializer.fields), {"titre", "slug"})
        empty = ArticleDefaultProtectedResource().as_viewset().serializer_class()
        self.assertEqual(dict(empty.fields), {})
        self.assertNotIn("owner", self.call("retrieve", slug="owned").data)

    def test_flat_many_to_many_relations_are_saved_before_after_hook(self):
        class UserResource(Resource):
            model = User
            fields = ["username", "groups"]

        resource = UserResource()
        group = Group.objects.create(name="API group")
        observed = []
        resource.after_save = lambda obj, request, is_new: observed.append(list(obj.groups.values_list("pk", flat=True)))
        response = self.call("create", "post", {"username": "new-user", "groups": [group.pk]}, resource=resource)
        self.assertEqual(response.status_code, 201)
        obj = User.objects.get(username="new-user")
        self.assertEqual(list(obj.groups.all()), [group])
        self.assertEqual(observed, [[group.pk]])
        response = self.call("partial_update", "patch", {"groups": []}, resource=resource, pk=obj.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed, [[group.pk], []])

    def test_router_registration_and_subclass_extension(self):
        from rest_framework.routers import SimpleRouter
        from django.urls import include, path, resolve
        import types

        class API(self.resource.as_viewset()):
            def get_queryset(inner):
                return super().get_queryset().filter(actif=True)

        router = SimpleRouter()
        router.register("articles", API, basename="api-article")
        urls = types.ModuleType("test_api_urls")
        urls.urlpatterns = [path("api/", include(router.urls))]
        with self.settings(ROOT_URLCONF=urls):
            match = resolve("/api/articles/owned/")
            self.assertEqual(match.kwargs, {"slug": "owned"})
            self.assertEqual(match.url_name, "api-article-detail")

    def test_serializer_validation_and_unauthenticated_writes(self):
        self.resource.before_save = Mock()
        for data in ({"titre": "Missing slug"}, {"titre": "Duplicate", "slug": "owned"}):
            self.assertEqual(self.call("create", "post", data).status_code, 400)
        response = self.call("create", "post", {"titre": "New", "slug": "new"}, user=None)
        self.assertIn(response.status_code, (401, 403))
        self.resource.before_save.assert_not_called()
        self.assertFalse(Article.objects.filter(slug="new").exists())

    def test_session_authentication_enforces_csrf(self):
        from rest_framework.test import APIClient
        from rest_framework.routers import SimpleRouter
        from django.urls import include, path
        from django.utils.crypto import get_random_string
        import types

        router = SimpleRouter()
        router.register("articles", self.resource.as_viewset(), basename="api-article")
        urls = types.ModuleType("test_csrf_api_urls")
        urls.urlpatterns = [path("api/", include(router.urls))]
        with self.settings(ROOT_URLCONF=urls):
            client = APIClient(enforce_csrf_checks=True)
            client.force_login(self.user)
            data = {"titre": "CSRF", "slug": "csrf"}
            self.assertEqual(client.post("/api/articles/", data, format="json").status_code, 403)
            self.assertFalse(Article.objects.filter(slug="csrf").exists())
            token = get_random_string(32)
            client.cookies["csrftoken"] = token
            response = client.post("/api/articles/", data, format="json", HTTP_X_CSRFTOKEN=token)
            self.assertEqual(response.status_code, 201)
            self.assertEqual(Article.objects.get(slug="csrf").owner, self.user)

    def test_after_delete_validation_error_rolls_back(self):
        self.resource.after_delete = Mock(side_effect=ValidationError("Late veto"))
        self.assertEqual(self.call("destroy", "delete", slug="owned").status_code, 400)
        self.assertTrue(Article.objects.filter(pk=self.article.pk).exists())
