from django.apps import AppConfig


class ServiceNow(AppConfig):
    name = 'service-now'
    verbose_name = 'ServiceNow'

    def ready(self):
        pass
