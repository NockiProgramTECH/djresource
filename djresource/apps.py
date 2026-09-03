from django.apps import AppConfig


class DjresourceConfig(AppConfig):
    """
    Configuration de l'app djresource.

    Doit être ajoutée à INSTALLED_APPS du projet hôte pour que Django
    trouve les templates fournis par la bibliothèque
    (djresource/templates/djresource/*.html).
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "djresource"
    verbose_name = "DjResource"
