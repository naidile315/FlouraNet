from django.apps import AppConfig


class NurseryAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nursery_app'

    def ready(self):
        # import signals
        try:
            import nursery_app.signals  # noqa: F401
        except Exception:
            pass
