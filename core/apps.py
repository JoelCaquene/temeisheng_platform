# core/apps.py

from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Importe seus sinais aqui para garantir que eles sejam registrados
        # Quando o Django inicia o aplicativo 'core', este método 'ready' é chamado,
        # e a importação de core.signals garante que as funções @receiver sejam conectadas.
        import core.signals
        