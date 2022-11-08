from django import forms

from .models import Website, Document


class WebsiteForm(forms.ModelForm):
    class Meta:
        model = Website
        fields = ["name", "url", "content"]


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["title", "date", "url"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}
