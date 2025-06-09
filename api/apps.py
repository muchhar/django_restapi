from django.apps import AppConfig

class MainConfig(AppConfig):
    name = 'api'
    def ready(self):
        from jobs import updater
        updater.start()