"""Admin models"""

# Django
from django import forms
from django.contrib import admin, messages

from .api import WandererApiError, audit_events
from .models import TrackedMap


class TrackedMapForm(forms.ModelForm):
    """Collapses slug/map_id into one value plus a picker.

    Wanderer's API accepts either identifier, never needs both, and offering two
    boxes invited filling in both — which left `_map_params` silently deciding
    for the user. One box and a dropdown makes the choice explicit, and writing
    the unused column back to "" keeps that promise in the database.
    """

    identifier_type = forms.ChoiceField(
        choices=[("slug", "Slug"), ("map_id", "Map ID")],
        initial="slug",
        label="Identify map by",
        help_text="Which identifier the value below is. Slug is the usual choice.",
    )
    identifier = forms.CharField(
        max_length=100,
        label="Slug or map ID",
        help_text=(
            "The slug from the map's URL in Wanderer (e.g. 'my-map'), or its "
            "UUID if you picked Map ID above. Only this one is stored."
        ),
    )

    class Meta:
        model = TrackedMap
        # slug/map_id are set in clean() from the two fields above.
        fields = ["name", "base_url", "api_token", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Editing: preselect whichever identifier this map actually uses.
        if self.instance and self.instance.pk:
            if self.instance.map_id:
                self.fields["identifier_type"].initial = "map_id"
                self.fields["identifier"].initial = self.instance.map_id
            else:
                self.fields["identifier_type"].initial = "slug"
                self.fields["identifier"].initial = self.instance.slug

    def clean(self):
        cleaned = super().clean()
        as_map_id = cleaned.get("identifier_type") == "map_id"
        value = (cleaned.get("identifier") or "").strip()

        # slug/map_id are excluded from Meta.fields, so _post_clean() skips
        # validating them on the instance. The field's own max_length covers the
        # longer column (slug); a map ID has a shorter one, so check it here.
        # Skip when the field already errored — required/max_length said it better.
        if as_map_id and "identifier" not in self.errors:
            limit = TrackedMap._meta.get_field("map_id").max_length
            if len(value) > limit:
                self.add_error("identifier", f"A map ID is at most {limit} characters.")

        # Assign here rather than in save(): _post_clean() validates the instance
        # right after this, and it won't overwrite fields absent from Meta.fields.
        if as_map_id:
            self.instance.map_id, self.instance.slug = value, ""
        else:
            self.instance.slug, self.instance.map_id = value, ""

        return cleaned


@admin.register(TrackedMap)
class TrackedMapAdmin(admin.ModelAdmin):
    form = TrackedMapForm
    list_display = ["name", "map_identifier", "has_api_key", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug", "map_id"]
    fields = [
        "name",
        "identifier_type",
        "identifier",
        "base_url",
        "api_token",
        "is_active",
    ]
    actions = ["test_api_key"]

    @admin.display(description="Identifier")
    def map_identifier(self, obj):
        if obj.map_id:
            return f"map ID: {obj.map_id}"

        return f"slug: {obj.slug}" if obj.slug else "—"

    @admin.display(boolean=True, description="API key")
    def has_api_key(self, obj):
        return obj.has_api_key

    @admin.action(description="Test the API key against Wanderer")
    def test_api_key(self, request, queryset):
        for tracked_map in queryset:
            try:
                # skip the cache so a freshly pasted key is actually exercised
                events = audit_events(tracked_map, use_cache=False)
            except WandererApiError as exc:
                # this action exists to debug a map, so show the full context
                self.message_user(request, exc.detail, level=messages.ERROR)
                continue

            self.message_user(
                request,
                f"{tracked_map.name}: OK, {len(events)} audit events available.",
                level=messages.SUCCESS,
            )
