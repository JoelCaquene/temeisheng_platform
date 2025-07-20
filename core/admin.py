# core/admin.py
from django.contrib import admin
from .models import User, SaldoUsuario, Nivel, Deposito, Saque, TarefaGanho, Convite, CoordenadaBancaria, ConfiguracaoPlataforma # Importe o novo modelo

# 1. Personaliza o Admin para o modelo User
class UserAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'first_name', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff')
    search_fields = ('phone_number', 'first_name', 'last_name') # Campos que serão pesquisáveis
    ordering = ('-date_joined',)

# 2. Personaliza o Admin para o modelo SaldoUsuario
class SaldoUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'saldo_acumulado', 'saldo_subsidio', 'nivel_ativo')
    list_filter = ('nivel_ativo',)
    search_fields = ('usuario__phone_number',) # Permite pesquisar pelo telefone do usuário relacionado
    raw_id_fields = ('usuario',) # Melhora a interface para selecionar o usuário

# 3. Personaliza o Admin para o modelo Nivel
class NivelAdmin(admin.ModelAdmin):
    list_display = ('nome', 'deposito_minimo', 'ganho_diario', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('nome',)
    ordering = ('deposito_minimo',)

# 4. Personaliza o Admin para o modelo Deposito
class DepositoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'valor', 'nivel_ativar', 'aprovado', 'data_solicitacao', 'data_aprovacao')
    list_filter = ('aprovado', 'nivel_ativar', 'data_solicitacao')
    search_fields = ('usuario__phone_number', 'valor', 'nivel_ativar__nome')
    raw_id_fields = ('usuario', 'nivel_ativar',)
    ordering = ('-data_solicitacao',)

# 5. Personaliza o Admin para o modelo Saque
class SaqueAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'valor', 'aprovado', 'data_solicitacao', 'data_aprovacao')
    list_filter = ('aprovado', 'data_solicitacao')
    search_fields = ('usuario__phone_number', 'valor', 'iban_cliente')
    raw_id_fields = ('usuario',)
    ordering = ('-data_solicitacao',)

# 6. Personaliza o Admin para o modelo TarefaGanho
class TarefaGanhoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'nivel', 'valor_ganho', 'data_ganho')
    list_filter = ('nivel', 'data_ganho')
    search_fields = ('usuario__phone_number', 'nivel__nome')
    raw_id_fields = ('usuario', 'nivel',)
    ordering = ('-data_ganho',)

# 7. Personaliza o Admin para o modelo Convite
class ConviteAdmin(admin.ModelAdmin):
    list_display = ('convidante', 'convidado', 'data_convite', 'subsidy_granted')
    list_filter = ('subsidy_granted', 'data_convite')
    search_fields = ('convidante__phone_number', 'convidado__phone_number')
    raw_id_fields = ('convidante', 'convidado',)
    ordering = ('-data_convite',)

# 8. Personaliza o Admin para o modelo CoordenadaBancaria
class CoordenadaBancariaAdmin(admin.ModelAdmin):
    list_display = ('nome_banco', 'iban', 'nome_titular', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('nome_banco', 'iban', 'nome_titular')
    ordering = ('nome_banco',)

# 9. Personaliza o Admin para o modelo ConfiguracaoPlataforma (NOVO)
class ConfiguracaoPlataformaAdmin(admin.ModelAdmin):
    list_display = ('whatsapp_numero', 'telegram_numero', 'whatsapp_grupo_link', 'telegram_grupo_link')
    # Não faz muito sentido ter search_fields ou list_filter para uma única instância
    def has_add_permission(self, request):
        # Permite adicionar apenas se não houver nenhuma instância ainda
        from .models import ConfiguracaoPlataforma # Importa localmente para evitar circular import
        return not ConfiguracaoPlataforma.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        # Permite deletar se houver uma instância, para poder recriar se necessário
        return True # Superuser pode deletar

# Registre seus modelos com as classes Admin personalizadas
admin.site.register(User, UserAdmin)
admin.site.register(SaldoUsuario, SaldoUsuarioAdmin)
admin.site.register(Nivel, NivelAdmin)
admin.site.register(Deposito, DepositoAdmin)
admin.site.register(Saque, SaqueAdmin)
admin.site.register(TarefaGanho, TarefaGanhoAdmin)
admin.site.register(Convite, ConviteAdmin)
admin.site.register(CoordenadaBancaria, CoordenadaBancariaAdmin)
admin.site.register(ConfiguracaoPlataforma, ConfiguracaoPlataformaAdmin) # Registre o novo modelo
