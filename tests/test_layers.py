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


class CSVTests(LayerTestCase):
    def rows(self, response):
        import csv
        import io
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertIn("attachment", response["Content-Disposition"])
        return list(csv.reader(io.StringIO(response.content.decode())))

    def test_export_applies_scope_search_filter_sort_but_not_pagination(self):
        from .resources import ArticleScopedResource
        resource = ArticleScopedResource()
        resource.search_fields = ["titre"]
        resource.ordering_fields = ["titre"]
        resource.paginate_by = 1
        resource.list_display = ["titre", "slug"]
        for titre, slug, owner, actif in [
            ("Match A", "a", self.user, True), ("Match B", "b", self.user, True),
            ("Match foreign", "foreign", None, True), ("Other", "other", self.user, True),
            ("Match inactive", "inactive", self.user, False),
        ]:
            Article.objects.create(titre=titre, slug=slug, owner=owner, actif=actif)
        response = resource.get_list_view().as_view()(self.request(data={
            "export": "csv", "q": "Match", "actif": "true", "sort": "titre",
            "dir": "desc", "page": "999",
        }))
        self.assertEqual(self.rows(response), [["titre", "slug"], ["Match B", "b"], ["Match A", "a"]])

    def test_csv_unicode_escaping_formulas_and_empty_results(self):
        resource = self.resource
        resource.list_display = ["titre"]
        view = resource.get_list_view().as_view()
        self.assertEqual(self.rows(view(self.request(data={"export": "csv"}))), [["titre"]])
        Article.objects.create(titre='Été, "riz"\nlocal', slug="a")
        Article.objects.create(titre='=HYPERLINK("bad")', slug="b")
        rows = self.rows(view(self.request(data={"export": "csv"})))
        self.assertIn(['Été, "riz"\nlocal'], rows)
        self.assertIn(['\'=HYPERLINK("bad")'], rows)

    def test_export_uses_list_permissions(self):
        from .resources import ArticleDefaultProtectedResource, ArticleBusinessProtectedResource
        from django.core.exceptions import PermissionDenied
        request = self.request(data={"export": "csv"}, user=AnonymousUser())
        self.assertEqual(ArticleDefaultProtectedResource().get_list_view().as_view()(request).status_code, 302)
        with self.assertRaises(PermissionDenied):
            ArticleBusinessProtectedResource().get_list_view().as_view()(
                self.request(data={"export": "csv"})
            )


class BulkActionTests(LayerTestCase):
    def setUp(self):
        super().setUp()
        self.article = Article.objects.create(titre="Mine", slug="mine", owner=self.user)
        self.other = Article.objects.create(titre="Other", slug="other")
        self.run = Mock(side_effect=lambda qs, request: qs.update(actif=False))
        self.resource.bulk_actions = [{"name": "archive", "label": "Archiver", "run": self.run}]

    def post(self, data=None, resource=None, **request_kwargs):
        resource = resource or self.resource
        return resource.get_list_view().as_view()(self.request("post", data or {
            "bulk_action": "archive", "selected": [self.article.pk],
        }, **request_kwargs))

    def test_only_selected_rows_and_object_actions(self):
        class Archive:
            name = "archive"
            label = "Archiver"

            def run(self, queryset, request):
                queryset.update(actif=False)

        self.resource.bulk_actions = [Archive()]
        response = self.post()
        self.assertEqual(response.status_code, 302)
        self.article.refresh_from_db()
        self.other.refresh_from_db()
        self.assertFalse(self.article.actif)
        self.assertTrue(self.other.actif)

    def test_forged_or_filtered_out_selection_rejects_everything(self):
        from .resources import ArticleScopedResource
        from django.core.exceptions import PermissionDenied
        resource = ArticleScopedResource()
        resource.bulk_actions = self.resource.bulk_actions
        for selected in ([self.other.pk], [self.article.pk, self.other.pk], [999999]):
            with self.subTest(selected=selected), self.assertRaises(PermissionDenied):
                self.post({"bulk_action": "archive", "selected": selected}, resource=resource)
        request = self.request("post", {"bulk_action": "archive", "selected": [self.article.pk]})
        request.GET = {"actif": "false"}
        with self.assertRaises(PermissionDenied):
            resource.get_list_view().as_view()(request)
        self.run.assert_not_called()

    def test_permissions_are_checked_before_running(self):
        from .resources import ArticleBusinessProtectedResource, ArticleDefaultProtectedResource
        from django.core.exceptions import PermissionDenied
        resource = ArticleDefaultProtectedResource()
        resource.bulk_actions = self.resource.bulk_actions
        self.assertEqual(self.post(resource=resource, user=AnonymousUser()).status_code, 302)
        resource = ArticleBusinessProtectedResource()
        resource.bulk_actions = self.resource.bulk_actions
        with self.assertRaises(PermissionDenied):
            self.post(resource=resource)
        self.resource.has_bulk_action_permission = lambda action, request: False
        with self.assertRaises(PermissionDenied):
            self.post()
        self.run.assert_not_called()

    def test_empty_unknown_and_malformed_selections(self):
        for data in ({"bulk_action": "archive"}, {"bulk_action": "unknown", "selected": [self.article.pk]},
                     {"bulk_action": "archive", "selected": ["not-a-pk"]}):
            self.assertEqual(self.post(data).status_code, 400)
        self.run.assert_not_called()
        self.resource.bulk_actions = []
        self.assertEqual(self.post().status_code, 405)

    def test_validation_error_rolls_back_action(self):
        from django.contrib.messages import ERROR, get_messages

        def reject(queryset, request):
            queryset.update(actif=False)
            raise ValidationError("Refus métier")

        self.resource.bulk_actions[0]["run"] = reject
        request = self.request("post", {"bulk_action": "archive", "selected": [self.article.pk]})
        response = self.resource.get_list_view().as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.article.refresh_from_db()
        self.assertTrue(self.article.actif)
        self.assertEqual([m.level for m in get_messages(request)], [ERROR])

    def test_deduplicated_selection_and_preserved_query(self):
        from django.http import QueryDict
        request = self.request("post", {"bulk_action": "archive", "selected": [self.article.pk] * 2})
        request.GET = QueryDict("q=Mine&sort=titre&dir=desc")
        response = self.resource.get_list_view().as_view()(request)
        self.assertEqual(response.url, "/articles/?q=Mine&sort=titre&dir=desc")
        self.run.assert_called_once()
        self.assertEqual(self.run.call_args.args[0].count(), 1)

    def test_controls_are_optional_on_all_themes_and_injected_lists(self):
        from django.template.loader import render_to_string
        for theme in ("bootstrap", "tailwind", "plain"):
            self.resource.theme = theme
            request = self.request(data={"q": "Mine"})
            response = self.resource.get_list_view().as_view()(request)
            self.assertContains(response, 'name="bulk_action"')
            self.assertContains(response, 'name="selected"')
            self.assertContains(response, 'name="csrfmiddlewaretoken"')
            self.assertContains(response, 'action="/articles/?q=Mine"')
            context = self.resource.get_list_context(request)
            content = render_to_string(self.resource._theme_template("list_partial", None), context, request=request)
            self.assertIn('name="bulk_action"', content)
            with self.subTest(theme=theme):
                self.resource.has_bulk_action_permission = lambda action, request: False
                response = self.resource.get_list_view().as_view()(request)
                self.assertNotContains(response, 'name="bulk_action"')
                self.assertNotContains(response, 'name="selected"')
                self.resource.has_bulk_action_permission = lambda action, request: True
        self.resource.bulk_actions = []
        self.assertNotContains(self.resource.get_list_view().as_view()(self.request()), 'name="selected"')

    def test_csrf_is_enforced_on_bulk_post(self):
        from django.test import Client, override_settings
        from django.urls import include, path
        import types
        urls = types.ModuleType("bulk_test_urls")
        urls.urlpatterns = [path("articles/", include(self.resource.urls()))]
        with override_settings(ROOT_URLCONF=urls):
            client = Client(enforce_csrf_checks=True)
            response = client.post("/articles/", {"bulk_action": "archive", "selected": [self.article.pk]})
            self.assertEqual(response.status_code, 403)
            client.get("/articles/")
            response = client.post("/articles/", {
                "bulk_action": "archive", "selected": [self.article.pk],
                "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
            })
            self.assertEqual(response.status_code, 302)
        self.run.assert_called_once()

    def test_invalid_action_configuration_is_rejected(self):
        from django.core.exceptions import ImproperlyConfigured
        for actions in ([{"name": "bad", "label": "Bad"}], self.resource.bulk_actions * 2):
            self.resource.bulk_actions = actions
            with self.assertRaises(ImproperlyConfigured):
                self.resource.get_bulk_actions(self.request())
