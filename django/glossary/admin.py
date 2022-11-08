from django.contrib import admin

from glossary.models import (
    Concept,
    Comment,
    Tag,
    AcceptanceState,
    AnnotationWorklog,
    ConceptDefined,
    ConceptOccurs,
    Lemma,
)

from django.urls import reverse
from django.utils.safestring import mark_safe


class ConceptOccursAdmin(admin.ModelAdmin):
    actions = ["delete_all_concept_occurs"]
    search_fields = ["id", "concept"]
    autocomplete_fields = ["concept", "document"]

    def delete_all_concept_occurs(self, request, queryset):
        ConceptOccurs.objects.all().delete()


class ConceptDefinedAdmin(admin.ModelAdmin):
    actions = ["delete_all_concept_defined"]
    search_fields = ["id", "concept"]
    autocomplete_fields = ["concept", "document"]

    def delete_all_concept_defined(self, request, queryset):
        ConceptDefined.objects.all().delete()


class LemmaAdmin(admin.ModelAdmin):
    actions = ["delete_all_lemmas"]
    search_fields = ["id", "name"]

    def delete_all_lemmas(self, request, queryset):
        Lemma.objects.all().delete()


class ConceptAdmin(admin.ModelAdmin):
    actions = ["delete_all_concepts", "delete_alle_lemmas", "delete_all_annotationworklogs"]
    search_fields = ["id", "name"]
    list_filter = ("website__name", "version")
    autocomplete_fields = ["other", "lemma_fk"]

    def delete_all_concepts(self, request, queryset):
        Concept.objects.all().delete()

    def delete_all_annotationworklogs(self, request, queryset):
        AnnotationWorklog.objects.all().delete()


class AcceptanceStateAdmin(admin.ModelAdmin):
    autocomplete_fields = ["concept"]
    list_filter = ("user__username", "updated_at")
    list_display = ["id", "user", "value", "updated_at"]


class AnnotationWorklogAdmin(admin.ModelAdmin):
    autocomplete_fields = ["document", "concept_occurs", "concept_defined"]
    list_filter = ("user__username", "updated_at")
    list_display = ["id", "user", "concept_occurs_link", "concept_defined_link", "updated_at"]

    def concept_occurs_link(self, obj):
        child = obj.concept_occurs
        if child:
            return self.get_link(obj, "occurrance")

    concept_occurs_link.short_description = "Occurance"

    def concept_defined_link(self, obj):
        child = obj.concept_defined
        if child:
            return self.get_link(obj, "definition")

    concept_occurs_link.short_description = "Definition"

    def get_link(self, obj, type):
        url = reverse("admin:{}_{}_change".format(obj._meta.app_label, obj._meta.model_name), args=(obj.pk,))
        return mark_safe('<a href="{}">{}</a>'.format(url, type))


class CommentAdmin(admin.ModelAdmin):
    autocomplete_fields = ["Concept"]
    list_filter = ("user__username", "updated_at")
    list_display = ["id", "user", "value", "updated_at"]


class TagAdmin(admin.ModelAdmin):
    autocomplete_fields = ["concept"]


admin.site.register(ConceptOccurs, ConceptOccursAdmin)
admin.site.register(ConceptDefined, ConceptDefinedAdmin)
admin.site.register(AnnotationWorklog, AnnotationWorklogAdmin)
admin.site.register(AcceptanceState, AcceptanceStateAdmin)
admin.site.register(Concept, ConceptAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Lemma, LemmaAdmin)
