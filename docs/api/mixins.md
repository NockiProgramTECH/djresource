# Mixins

Les vues générées sont composées dynamiquement par `Resource` à partir de
mixins **mono-responsables**, chacun chaînant `super()`. Ils sont volontairement
combinables librement — c'est ce qui permet à `Resource` de construire des CBV
sur mesure avec `type()`.

## Contexte commun

::: djresource.mixins.ResourceContextMixin

::: djresource.mixins.ResourceListContextMixin

## Résolution de l'objet via `lookup_field`

::: djresource.mixins.ResourceLookupMixin

## Recherche et tri (ListView)

::: djresource.mixins.ResourceSearchMixin

::: djresource.mixins.ResourceOrderingMixin

## Messages de succès

::: djresource.mixins.ResourceCreateMessageMixin

::: djresource.mixins.ResourceUpdateMessageMixin

::: djresource.mixins.ResourceDeleteMessageMixin
