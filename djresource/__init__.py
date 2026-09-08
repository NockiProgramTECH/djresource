"""
djresource
==========

Bibliothèque Django qui génère automatiquement les vues CRUD
(Create, Read, Update, Delete), le formulaire et les routes d'un modèle,
via une classe `Resource` à hériter.

Voir djresource/resource.py pour le point d'entrée principal.
"""

__version__ = "0.1.0"

from .resource import FieldsAllWarning, Resource

__all__ = ["FieldsAllWarning", "Resource", "__version__"]
