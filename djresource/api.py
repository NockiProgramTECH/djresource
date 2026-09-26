"""Lazy, optional Django REST Framework bridge; importing core needs no DRF.

Call Resource.as_viewset() after Django setup. No routes are registered here.
DRF imports happen only inside build_viewset(), with an actionable error when
it is unavailable. See the factory docstring for supported behavior and limits.
"""
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import HttpResponse
from django.views import View

from .signals import resource_post_delete, resource_post_save, resource_pre_save


def build_viewset(resource):
    """Build an override-friendly ModelViewSet and ModelSerializer for a Resource.

    Reuses explicit fields (no implicit exposure), readonly_fields, lookup,
    scoped queryset, search/ordering allowlists, list_filter and paginate_by.
    DRF's query parameters are search, ordering and page, not HTML q/sort/dir.
    Authentication follows project DRF settings; a BasePermission adapter runs
    Resource.get_permissions() mixins with the authenticated DRF request.
    Custom permission mixins must delegate dispatch to super() to grant access;
    only request, kwargs, resource, action, get_queryset/get_object and Resource
    permission attributes are exposed by the probe, not HTML form/context APIs.

    Writes call Resource hooks and signals atomically (including M2M). DRF
    serializer validation replaces ModelForm validation; model.full_clean() is
    not automatic. Nested writes, HTML inline formsets, bulk actions, CSV, widget
    settings and custom ModelForms are not exposed. FK/M2M choices are not scoped
    automatically: customize the generated serializer to authorize related IDs.
    Resource/serializer hooks see a DRF Request, not the underlying HttpRequest.
    Use on_commit() for external side effects. Subclasses replacing serializers
    or perform_* methods must preserve any required business hooks themselves.
    """
    try:
        from rest_framework import filters, permissions, serializers, viewsets
        from rest_framework.pagination import PageNumberPagination
        from rest_framework.utils import model_meta
    except ImportError as exc:
        raise ImproperlyConfigured(
            "Resource.as_viewset() requires Django REST Framework. "
            "Install djresource[api] or djangorestframework."
        ) from exc

    class PermissionEndpoint(View):
        def allow(self, request, *args, **kwargs):
            self.permission_granted = True
            return HttpResponse(status=204)

        get = post = put = patch = delete = head = options = allow

    class ResourcePermission(permissions.BasePermission):
        """Run the Resource's Django permission dispatch chain, failing closed."""

        def has_permission(self, request, view):
            attrs = {
                **resource._permission_view_attrs(),
                "permission_granted": False,
                "action": view.action,
                "get_queryset": lambda probe: view.get_queryset(),
                "get_object": lambda probe: view.get_object(),
            }
            probe = type("ResourceAPIPermissionProbe", (
                *resource.get_permissions(), PermissionEndpoint,
            ), attrs)()
            probe.setup(request, *view.args, **view.kwargs)
            try:
                response = probe.dispatch(request, *view.args, **view.kwargs)
            except PermissionDenied:
                return False
            return probe.permission_granted and 200 <= response.status_code < 300

    def validation_error(exc):
        return serializers.ValidationError(
            exc.message_dict if hasattr(exc, "message_dict") else {"non_field_errors": exc.messages}
        )

    class ResourceSerializer(serializers.ModelSerializer):
        """Flat serializer preserving hooks/signals for parent and M2M writes."""

        def save_instance(self, instance, validated_data, is_new):
            request = self.context["request"]
            relations = model_meta.get_field_info(instance).relations
            many_to_many = []
            for attr, value in validated_data.items():
                if attr in relations and relations[attr].to_many:
                    many_to_many.append((attr, value))
                else:
                    setattr(instance, attr, value)
            try:
                with transaction.atomic():
                    resource.clean(instance, request)
                    resource.before_save(instance, request, is_new)
                    resource_pre_save.send(sender=resource.model, instance=instance, resource=resource)
                    instance.save()
                    for attr, value in many_to_many:
                        getattr(instance, attr).set(value)
                    resource.after_save(instance, request, is_new)
                    resource_post_save.send(sender=resource.model, instance=instance, resource=resource)
            except DjangoValidationError as exc:
                raise validation_error(exc) from exc
            return instance

        def create(self, validated_data):
            serializers.raise_errors_on_nested_writes("create", self, validated_data)
            return self.save_instance(resource.model(), validated_data, is_new=True)

        def update(self, instance, validated_data):
            serializers.raise_errors_on_nested_writes("update", self, validated_data)
            return self.save_instance(instance, validated_data, is_new=False)

    ResourceSerializer.Meta = type("Meta", (), {
        "model": resource.model,
        "fields": "__all__" if resource.fields == "__all__" else tuple(resource.fields),
        "read_only_fields": tuple(resource.readonly_fields),
    })
    ResourceSerializer.__name__ = f"{resource.model.__name__}ResourceSerializer"

    class ResourcePagination(PageNumberPagination):
        page_size = resource.paginate_by

    class ResourceViewSet(viewsets.ModelViewSet):
        serializer_class = ResourceSerializer
        permission_classes = [ResourcePermission]
        filter_backends = [filters.SearchFilter, filters.OrderingFilter]
        pagination_class = ResourcePagination

        def get_queryset(self):
            queryset = self.resource.get_queryset(self.request)
            return self.resource.apply_list_filters(queryset, self.request.query_params)

        def perform_destroy(self, instance):
            try:
                with transaction.atomic():
                    self.resource.before_delete(instance, self.request)
                    instance.delete()
                    self.resource.after_delete(instance, self.request)
                    resource_post_delete.send(
                        sender=self.resource.model, instance=instance, resource=self.resource,
                    )
            except DjangoValidationError as exc:
                raise validation_error(exc) from exc

    ResourceViewSet.resource = resource
    ResourceViewSet.search_fields = tuple(resource.search_fields)
    ResourceViewSet.ordering_fields = tuple(resource.ordering_fields)
    ResourceViewSet.lookup_field = resource.lookup_field
    ResourceViewSet.lookup_url_kwarg = resource.lookup_url_kwarg
    ResourceViewSet.__name__ = f"{resource.model.__name__}ResourceViewSet"
    return ResourceViewSet
