# core/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views # Importa as views de autenticação do Django

urlpatterns = [
    path('', views.login_view, name='login'), # Define a raiz como a página de login
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('menu/', views.menu_view, name='menu'),
    path('logout/', views.logout_view, name='logout'),
    path('deposito/', views.deposito_view, name='deposito'),
    path('saque/', views.saque_view, name='saque'),
    path('tarefa/', views.tarefa_view, name='tarefa'),
    path('nivel/', views.nivel_view, name='nivel'),
    path('minha_equipe/', views.minha_equipe_view, name='minha_equipe'), # Corrigido de 'equipa' para 'minha_equipe'
    path('perfil/', views.perfil_view, name='perfil'),
    path('update-profile/', views.update_profile_view, name='update_profile'), # Para a atualização de nome

    # URLs para alteração de senha (logado)
    path('alterar-senha/', views.CustomPasswordChangeView.as_view(), name='alterar_senha'), # Corrigido de 'change_password' para 'alterar_senha'

    # URLs para redefinição de senha (esqueci minha senha - deslogado)
    path('reset_password/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('reset_password_done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset_password_complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('sobre/', views.sobre_view, name='sobre'), # Adicionado a URL para a página "Sobre"
]
