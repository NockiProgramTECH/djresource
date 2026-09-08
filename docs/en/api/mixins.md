# Mixins

The generated views are dynamically composed by `Resource` from
**single-responsibility** mixins, each chaining `super()`. They are deliberately
freely combinable — this is what allows `Resource` to build custom CBVs
with `type()`.

## Shared context

::: djresource.mixins.ResourceContextMixin

::: djresource.mixins.ResourceListContextMixin

## Object resolution via `lookup_field`

::: djresource.mixins.ResourceLookupMixin

## Search and sorting (ListView)

::: djresource.mixins.ResourceSearchMixin

::: djresource.mixins.ResourceOrderingMixin

## Success messages

::: djresource.mixins.ResourceCreateMessageMixin

::: djresource.mixins.ResourceUpdateMessageMixin

::: djresource.mixins.ResourceDeleteMessageMixin
