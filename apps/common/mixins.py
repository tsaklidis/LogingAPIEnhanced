class OwnerFilterMixin:
    """
    Mixin that filters querysets by the authenticated user's ownership chain.
    Expects `owner_filter_field` to be set on the view.
    """

    owner_filter_field = "owner"

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(**{self.owner_filter_field: self.request.user})
