from django.db import models
from django.utils import timezone


class DbQuery(models.Model):
    query = models.TextField()
    rdf_query = models.TextField(default="")

    class App(models.TextChoices):
        NONE = "------"
        SEARCHAPP = "searchapp"
        GLOSSARY = "glossary"
        OBLIGATIONS = "obligations"
        SCHEDULER = "scheduler"

    app = models.CharField(max_length=50, choices=sorted(App.choices), default=App.NONE, db_index=True)

    user = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)
