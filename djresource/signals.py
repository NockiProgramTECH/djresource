"""Optional Django CRUD notifications, complementing Resource hooks.

All signals send sender=resource.model, instance=instance, resource=resource.
They are synchronous (receiver errors propagate), not commit notifications.
Post-save fires after parent/M2M hooks but before inline saving. Use
transaction.on_commit() for external side effects. Post-delete's instance has
its pk cleared by Django. QuerySet.update/delete and bulk actions do not emit
these resource signals automatically.
"""
from django.dispatch import Signal

resource_pre_save = Signal()
resource_post_save = Signal()
resource_post_delete = Signal()
