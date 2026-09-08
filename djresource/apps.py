from django.apps import AppConfig


class DjresourceConfig(AppConfig):
    """
    Configuration for the djresource app.

    Must be added to the host project's INSTALLED_APPS so that Django
    finds the templates provided by the library
    (djresource/templates/djresource/*.html).
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "djresource"
    verbose_name = "DjResource"
