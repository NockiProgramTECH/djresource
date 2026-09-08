from django.db import models


class Produit(models.Model):
    """Modèle de test : un produit (contexte FCFA)."""

    nom = models.CharField("Nom", max_length=100)
    prix = models.DecimalField("Prix (FCFA)", max_digits=10, decimal_places=0)
    stock = models.PositiveIntegerField("Stock", default=0)
    actif = models.BooleanField("Actif", default=True)
    cree_le = models.DateTimeField("Créé le", auto_now_add=True)

    class Meta:
        verbose_name = "produit"
        verbose_name_plural = "produits"
        ordering = ["-cree_le"]

    def __str__(self):
        return self.nom


class Article(models.Model):
    """Modèle de test pour le lookup par slug et les filtres de liste."""

    ETAT_BROUILLON = "brouillon"
    ETAT_PUBLIE = "publie"

    ETATS = [
        (ETAT_BROUILLON, "Brouillon"),
        (ETAT_PUBLIE, "Publié"),
    ]

    titre = models.CharField("Titre", max_length=100)
    slug = models.SlugField("Slug", max_length=100, unique=True)
    actif = models.BooleanField("Actif", default=True)
    etat = models.CharField(
        "État", max_length=20, choices=ETATS, default=ETAT_PUBLIE
    )

    class Meta:
        verbose_name = "article"
        verbose_name_plural = "articles"
        ordering = ["titre"]

    def __str__(self):
        return self.titre
