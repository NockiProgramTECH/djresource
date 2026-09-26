"""
Tests d'intégration qui valident que le CRUD généré par djresource
fonctionne de bout en bout sur un modèle de test.
"""
import warnings

from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse

from djresource.resource import FieldsAllWarning, Resource

from .models import Article, Produit
from .resources import (
    ArticleBusinessProtectedResource,
    ArticleDefaultProtectedResource,
    ArticleProtegeResource,
    ArticleResource,
    ArticleScopedResource,
)


class ProduitToutChampsResource(Resource):
    """Resource laissée avec le défaut `fields = "__all__"` (à éviter)."""

    model = Produit
    fields = "__all__"


class FieldsExplicitesTests(TestCase):
    """
    SÉCURITÉ : `fields = "__all__"` (défaut) expose tous les champs du
    modèle dans le formulaire (mass assignment). Un avertissement doit être
    émis à l'instanciation pour inciter à déclarer les champs explicitement.
    """

    def test_fields_all_emmet_un_avertissement(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ProduitToutChampsResource()
        self.assertTrue(
            any(issubclass(w.category, FieldsAllWarning) for w in caught),
            "fields='__all__' doit émettre un FieldsAllWarning",
        )

    def test_fields_explicites_pas_d_avertissement(self):
        from .resources import ProduitResource  # import local pour la lisibilité

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ProduitResource()
        self.assertFalse(
            any(issubclass(w.category, FieldsAllWarning) for w in caught),
            "fields explicites ne doit PAS émettre de FieldsAllWarning",
        )


class ArticleSlugLookupTests(TestCase):
    """
    Valide le paramètre `lookup_field` de Resource : les URLs de détail /
    modification / suppression utilisent un autre champ que le pk (ici
    "slug" sur le modèle Article).
    """

    def setUp(self):
        self.article = Article.objects.create(titre="Riz local", slug="riz-local")

    def test_pattern_url_du_slug(self):
        self.assertEqual(ArticleResource().get_lookup_url(), "<slug:slug>")

    def test_detail_par_slug(self):
        url = reverse("article_detail", args=["riz-local"])
        self.assertEqual(url, "/articles/riz-local/")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Riz local")

    def test_modification_par_slug(self):
        response = self.client.post(
            reverse("article_update", args=["riz-local"]),
            {"titre": "Riz local (promo)", "slug": "riz-local"},
        )
        self.assertRedirects(response, reverse("article_list"))
        self.article.refresh_from_db()
        self.assertEqual(self.article.titre, "Riz local (promo)")

    def test_suppression_par_slug(self):
        response = self.client.post(reverse("article_delete", args=["riz-local"]))
        self.assertRedirects(response, reverse("article_list"))
        self.assertFalse(Article.objects.filter(pk=self.article.pk).exists())

    def test_slug_inconnu_retourne_404(self):
        response = self.client.get(reverse("article_detail", args=["introuvable"]))
        self.assertEqual(response.status_code, 404)

    def test_valeur_lookup(self):
        self.assertEqual(ArticleResource().get_lookup_value(self.article), "riz-local")


class PartialPermissionsTests(TestCase):
    """
    SÉCURITÉ : les partiels injectés (`get_list_context`, `get_form_context`,
    `get_detail_context`) doivent appliquer les permissions de la Resource
    (`get_permissions()`), comme le font les pages pleine page via dispatch().
    Un visiteur anonyme sur une Resource protégée par LoginRequiredMixin ne
    doit PAS pouvoir obtenir le contexte d'un composant injecté.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.resource = ArticleProtegeResource()
        self.article = Article.objects.create(titre="Riz local", slug="riz-local")
        self.user = User.objects.create_user(username="alice", password="secret")

    def _request(self, user):
        request = self.factory.get("/")
        # RequestFactory ne passe pas par AuthenticationMiddleware.
        request.user = user
        return request

    def test_liste_partielle_refuse_anonyme(self):
        with self.assertRaises(PermissionDenied):
            self.resource.get_list_context(self._request(AnonymousUser()))

    def test_liste_partielle_autorise_connecte(self):
        context = self.resource.get_list_context(self._request(self.user))
        self.assertIn("object_list", context)

    def test_detail_partiel_refuse_anonyme(self):
        with self.assertRaises(PermissionDenied):
            self.resource.get_detail_context(self._request(AnonymousUser()), "riz-local")

    def test_detail_partiel_autorise_connecte(self):
        context = self.resource.get_detail_context(self._request(self.user), "riz-local")
        self.assertEqual(context["object"].slug, "riz-local")

    def test_formulaire_partiel_refuse_anonyme(self):
        with self.assertRaises(PermissionDenied):
            self.resource.get_form_context(self._request(AnonymousUser()))

    def test_formulaire_partiel_autorise_connecte(self):
        context = self.resource.get_form_context(self._request(self.user))
        self.assertIn("form", context)

    def test_permissions_metier_des_partiels_sont_appliquees(self):
        resource = ArticleBusinessProtectedResource()
        denied = User.objects.create_user(username="denied", password="pw")
        with self.assertRaises(PermissionDenied):
            resource.get_list_context(self._request(denied))


class DefaultSecurityTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.article = Article.objects.create(titre="Privé", slug="prive")

    def test_crud_est_protege_par_defaut(self):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        response = ArticleDefaultProtectedResource().get_list_view().as_view()(
            request
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_publicite_est_explicite(self):
        response = self.client.get(reverse("article_list"))
        self.assertEqual(response.status_code, 200)

    def test_champs_par_defaut_ne_permettent_pas_le_mass_assignment(self):
        resource = ArticleDefaultProtectedResource()
        self.assertEqual(list(resource.get_form_class().base_fields), [])


class QuerysetScopeTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw")
        self.bob = User.objects.create_user(username="bob", password="pw")
        self.alice_article = Article.objects.create(
            titre="Alice", slug="alice", owner=self.alice
        )
        self.bob_article = Article.objects.create(
            titre="Bob", slug="bob", owner=self.bob
        )
        self.resource = ArticleScopedResource()

    def test_liste_et_lookup_sont_isoles_par_utilisateur(self):
        list_request = RequestFactory().get("/")
        list_request.user = self.alice
        response = self.resource.get_list_view().as_view()(list_request)
        self.assertContains(response, "Alice")
        self.assertNotContains(response, "Bob")
        detail_request = RequestFactory().get("/")
        detail_request.user = self.alice
        with self.assertRaises(Http404):
            self.resource.get_detail_view().as_view()(
                detail_request, slug=self.bob_article.slug
            )

    def test_update_delete_ne_peuvent_pas_franchir_le_scope(self):
        update_request = RequestFactory().post(
            "/", {"titre": "Hijacked", "slug": self.bob_article.slug}
        )
        update_request.user = self.alice
        delete_request = RequestFactory().post("/")
        delete_request.user = self.alice
        with self.assertRaises(Http404):
            self.resource.get_update_view().as_view()(
                update_request, slug=self.bob_article.slug
            )
        with self.assertRaises(Http404):
            self.resource.get_delete_view().as_view()(
                delete_request, slug=self.bob_article.slug
            )
        self.bob_article.refresh_from_db()
        self.assertEqual(self.bob_article.titre, "Bob")
        self.assertTrue(Article.objects.filter(pk=self.bob_article.pk).exists())


class ArticleFilterTests(TestCase):
    """
    Valide `list_filter` : filtrage de la liste par `?<champ>=<valeur>`,
    restreint aux champs déclarés (booléen et champ à `choices` ici).
    """

    def setUp(self):
        self.actif = Article.objects.create(
            titre="Riz local", slug="riz-local", actif=True,
            etat=Article.ETAT_PUBLIE,
        )
        self.brouillon = Article.objects.create(
            titre="Savon", slug="savon", actif=False,
            etat=Article.ETAT_BROUILLON,
        )

    def test_liste_affiche_tous_sans_filtre(self):
        response = self.client.get(reverse("article_list"))
        self.assertContains(response, "Riz local")
        self.assertContains(response, "Savon")

    def test_filtre_boolean_oui(self):
        response = self.client.get(reverse("article_list"), {"actif": "1"})
        self.assertContains(response, "Riz local")
        self.assertNotContains(response, "Savon")

    def test_filtre_boolean_non(self):
        response = self.client.get(reverse("article_list"), {"actif": "0"})
        self.assertNotContains(response, "Riz local")
        self.assertContains(response, "Savon")

    def test_filtre_choices(self):
        response = self.client.get(
            reverse("article_list"), {"etat": Article.ETAT_BROUILLON}
        )
        self.assertNotContains(response, "Riz local")
        self.assertContains(response, "Savon")

    def test_select_de_filtre_present(self):
        # Le template de liste expose un <select> par champ de list_filter.
        response = self.client.get(reverse("article_list"))
        self.assertContains(response, 'name="actif"')
        self.assertContains(response, 'name="etat"')

    def test_combinaison_recherche_et_filtre(self):
        # q et un filtre actif se cumulent.
        response = self.client.get(reverse("article_list"), {"q": "riz", "actif": "1"})
        self.assertContains(response, "Riz local")
        self.assertNotContains(response, "Savon")


class ProduitCrudTests(TestCase):
    def setUp(self):
        self.produit = Produit.objects.create(nom="Riz local", prix=15000, stock=50)

    def test_liste_produits_affiche_les_objets(self):
        response = self.client.get(reverse("produit_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Riz local")

    def test_creation_produit(self):
        response = self.client.post(reverse("produit_create"), {
            "nom": "Huile 1L",
            "prix": 2500,
            "stock": 30,
            "actif": True,
        })
        self.assertRedirects(response, reverse("produit_list"))
        self.assertTrue(Produit.objects.filter(nom="Huile 1L").exists())

    def test_modification_produit(self):
        response = self.client.post(
            reverse("produit_update", args=[self.produit.pk]),
            {"nom": "Riz local (promo)", "prix": 12000, "stock": 50, "actif": True},
        )
        self.assertRedirects(response, reverse("produit_list"))
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.nom, "Riz local (promo)")

    def test_suppression_produit(self):
        response = self.client.post(reverse("produit_delete", args=[self.produit.pk]))
        self.assertRedirects(response, reverse("produit_list"))
        self.assertFalse(Produit.objects.filter(pk=self.produit.pk).exists())

    def test_recherche_filtre_les_resultats(self):
        Produit.objects.create(nom="Savon", prix=500, stock=100)
        response = self.client.get(reverse("produit_list"), {"q": "riz"})
        self.assertContains(response, "Riz local")
        self.assertNotContains(response, "Savon")

    def test_detail_affiche_l_objet(self):
        response = self.client.get(reverse("produit_detail", args=[self.produit.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Riz local")


class BusinessHooksTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="hook-owner")

    def request(self, data=None):
        from django.contrib.messages.storage.fallback import FallbackStorage
        request = self.factory.post("/articles/nouveau/", data or {})
        request.user = self.user
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def test_scoped_creation_assigns_owner_and_calls_after_save(self):
        from unittest.mock import Mock
        resource = ArticleScopedResource()
        resource.after_save = Mock()
        response = resource.get_create_view().as_view()(
            self.request({"titre": "Owned", "slug": "owned"})
        )
        self.assertEqual(response.status_code, 302)
        article = Article.objects.get(slug="owned")
        self.assertEqual(article.owner, self.user)
        resource.after_save.assert_called_once()
        saved, request, is_new = resource.after_save.call_args.args
        self.assertEqual(saved.pk, article.pk)
        self.assertTrue(is_new)

    def test_update_hooks(self):
        from unittest.mock import Mock
        article = Article.objects.create(titre="Old", slug="old", owner=self.user)
        resource = ArticleScopedResource()
        resource.after_save = Mock()
        response = resource.get_update_view().as_view()(
            self.request({"titre": "New", "slug": "old"}), slug="old"
        )
        self.assertEqual(response.status_code, 302)
        article.refresh_from_db()
        self.assertEqual(article.titre, "New")
        self.assertFalse(resource.after_save.call_args.args[2])

    def test_delete_veto_has_no_success_message(self):
        from unittest.mock import Mock
        from django.core.exceptions import ValidationError
        from django.contrib.messages import get_messages, ERROR
        article = Article.objects.create(titre="Keep", slug="keep")
        resource = ArticleResource()
        resource.before_delete = Mock(side_effect=ValidationError("Keep it"))
        resource.after_delete = Mock()
        request = self.request()
        response = resource.get_delete_view().as_view()(request, slug=article.slug)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Article.objects.filter(pk=article.pk).exists())
        resource.after_delete.assert_not_called()
        self.assertEqual([m.level for m in get_messages(request)], [ERROR])

    def inline_data(self, **extra):
        return {"titre": "Parent", "slug": "parent", "notes-TOTAL_FORMS": "1",
                "notes-INITIAL_FORMS": "0", "notes-0-text": "Child", **extra}

    def test_inline_saved_after_parent(self):
        from .resources import ArticleInlineResource
        from .models import ArticleNote
        response = ArticleInlineResource().get_create_view().as_view()(
            self.request(self.inline_data())
        )
        self.assertEqual(response.status_code, 302)
        note = ArticleNote.objects.get()
        self.assertEqual(note.article_id, Article.objects.get(slug="parent").pk)
        self.assertEqual(note.article.owner, self.user)

    def test_clean_veto_does_not_save_parent_or_inline(self):
        from unittest.mock import Mock
        from django.core.exceptions import ValidationError
        from .resources import ArticleInlineResource
        from .models import ArticleNote
        resource = ArticleInlineResource()
        resource.clean = Mock(side_effect=ValidationError("Rejected"))
        response = resource.get_create_view().as_view()(self.request(self.inline_data()))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rejected")
        self.assertContains(response, 'value="Child"')
        self.assertFalse(Article.objects.exists())
        self.assertFalse(ArticleNote.objects.exists())

    def test_invalid_inline_does_not_save_parent(self):
        from .resources import ArticleInlineResource
        response = ArticleInlineResource().get_create_view().as_view()(
            self.request(self.inline_data(**{"notes-0-text": "x" * 101}))
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Article.objects.exists())

    def test_inline_failure_rolls_back_parent(self):
        from unittest.mock import patch
        from .resources import ArticleInlineResource
        from .models import ArticleNote
        with patch.object(ArticleNote, "save", side_effect=RuntimeError("storage")):
            with self.assertRaises(RuntimeError):
                ArticleInlineResource().get_create_view().as_view()(
                    self.request(self.inline_data())
                )
        self.assertFalse(Article.objects.exists())
