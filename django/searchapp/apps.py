from django.apps import AppConfig


class SearchAppConfig(AppConfig):
    name = "searchapp"

    def ready(self):
        import searchapp.signals
