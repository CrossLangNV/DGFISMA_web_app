from django.contrib import admin

# Register your models here.
from obligations.models import (
    ReportingObligation,
    Comment,
    Tag,
    AcceptanceState,
    ROAnnotationWorklog,
    ReportingObligationOffsets,
)

from django.urls import reverse
from django.utils.safestring import mark_safe


class ReportingObligationAdmin(admin.ModelAdmin):
    actions = ["delete_all_reporting_obligations"]
    search_fields = ["id", "name"]

    def delete_all_reporting_obligations(self, request, queryset):
        ReportingObligation.objects.all().delete()


class AcceptanceStateAdmin(admin.ModelAdmin):
    autocomplete_fields = ["reporting_obligation"]
    list_filter = ("user__username", "updated_at")
    list_display = ["id", "user", "value", "updated_at"]


class CommentAdmin(admin.ModelAdmin):
    autocomplete_fields = ["reporting_obligation"]
    list_filter = ("user__username", "updated_at")
    list_display = ["id", "user", "value", "updated_at"]


class TagAdmin(admin.ModelAdmin):
    autocomplete_fields = ["reporting_obligation"]


class ROAnnotationWorklogAdmin(admin.ModelAdmin):
    autocomplete_fields = ["ro_offsets"]
    list_filter = ("user__username", "updated_at")
    list_display = ["id", "user", "ro_offsets_link", "updated_at"]

    def ro_offsets_link(self, obj):
        child = obj.ro_offsets
        if child:
            return self.get_link(obj, "offsets")

    ro_offsets_link.short_description = "Offsets"

    def get_link(self, obj, type):
        url = reverse("admin:{}_{}_change".format(obj._meta.app_label, obj._meta.model_name), args=(obj.pk,))
        return mark_safe('<a href="{}">{}</a>'.format(url, type))


class ReportingObligationOffsetsAdmin(admin.ModelAdmin):
    search_fields = ["id"]
    autocomplete_fields = ["ro", "document"]


admin.site.register(ReportingObligation, ReportingObligationAdmin)
admin.site.register(AcceptanceState, AcceptanceStateAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(ROAnnotationWorklog, ROAnnotationWorklogAdmin)
admin.site.register(ReportingObligationOffsets, ReportingObligationOffsetsAdmin)
