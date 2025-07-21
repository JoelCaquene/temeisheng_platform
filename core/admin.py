# core/admin.py (CORREÇÕES PONTUAIS CONFORME SOLICITADO E ADIÇÃO DE saldo_subsidy)
from django.contrib import admin
from django.utils import timezone # Adicionado para 'data_aprovacao' nos actions

from .models import User, SaldoUsuario, Nivel, Deposito, Saque, TarefaGanho, Convite, CoordenadaBancaria, ConfiguracaoPlataforma # Importe o novo modelo

# 1. Personaliza o Admin para o modelo User
class UserAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'first_name', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff')
    search_fields = ('phone_number', 'first_name', 'last_name') # Campos que serão pesquisáveis
    ordering = ('-date_joined',)
    # Adicionei os campos de convite para visualização, pois eles são relevantes para a equipe
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Informações Pessoais', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas Importantes', {'fields': ('last_login', 'date_joined')}),
        ('Convites', {'fields': ('referral_code', 'referred_by')}), # Adicionado para visualização
    )
    readonly_fields = ('last_login', 'date_joined', 'referral_code') # referral_code é gerado automaticamente


# 2. Personaliza o Admin para o modelo SaldoUsuario
class SaldoUsuarioAdmin(admin.ModelAdmin):
    # CORREÇÃO: Adicionado 'saldo_subsidy' aqui para que ele apareça no Django Admin
    list_display = ('usuario', 'saldo_acumulado', 'saldo_subsidy', 'nivel_ativo', 'nivel_expirado') # 'nivel_expirado' é um @property do modelo
    list_filter = ('nivel_ativo',)
    search_fields = ('usuario__phone_number',) # Permite pesquisar pelo telefone do usuário relacionado
    raw_id_fields = ('usuario',) # Melhora a interface para selecionar o usuário

# 3. Personaliza o Admin para o modelo Nivel
class NivelAdmin(admin.ModelAdmin):
    list_display = ('nome', 'deposito_minimo', 'ganho_diario', 'is_active', 'periodo_dias') # Adicionado periodo_dias
    list_filter = ('is_active',)
    search_fields = ('nome',)
    ordering = ('deposito_minimo',)

# 4. Personaliza o Admin para o modelo Deposito
class DepositoAdmin(admin.ModelAdmin):
    # CORRIGIDO: 'aprovado' não é um campo; 'status' é o campo que contém 'aprovado', 'pendente', 'rejeitado'.
    list_display = ('usuario', 'valor', 'nivel_ativar', 'status', 'data_solicitacao', 'data_aprovacao')
    # CORRIGIDO: 'aprovado' não é um campo; 'status' é o campo.
    list_filter = ('status', 'nivel_ativar', 'data_solicitacao')
    search_fields = ('usuario__phone_number', 'valor', 'nivel_ativar__nome')
    raw_id_fields = ('usuario', 'nivel_ativar',)
    ordering = ('-data_solicitacao',)
    actions = ['approve_deposits', 'reject_deposits'] # Mantido os actions

    def approve_deposits(self, request, queryset):
        for deposito in queryset:
            if deposito.status != 'aprovado':
                deposito.status = 'aprovado'
                deposito.data_aprovacao = timezone.now()
                deposito.save() # O signal handle_deposit_approval será disparado aqui
        self.message_user(request, "Depósitos selecionados foram aprovados com sucesso.")
    approve_deposits.short_description = "Aprovar Depósitos Selecionados"

    def reject_deposits(self, request, queryset):
        queryset.update(status='rejeitado')
        self.message_user(request, "Depósitos selecionados foram rejeitados.")
    reject_deposits.short_description = "Rejeitar Depósitos Selecionados"


# 5. Personaliza o Admin para o modelo Saque
class SaqueAdmin(admin.ModelAdmin):
    # CORRIGIDO: 'aprovado' não é um campo; 'status' é o campo.
    list_display = ('usuario', 'valor', 'status', 'data_solicitacao', 'data_aprovacao')
    # CORRIGIDO: 'aprovado' não é um campo; 'status' é o campo.
    list_filter = ('status', 'data_solicitacao')
    search_fields = ('usuario__phone_number', 'valor', 'iban_cliente')
    raw_id_fields = ('usuario',)
    ordering = ('-data_solicitacao',)
    actions = ['approve_saques', 'reject_saques'] # Mantido os actions

    def approve_saques(self, request, queryset):
        for saque in queryset:
            if saque.status != 'aprovado':
                saque.status = 'aprovado'
                saque.data_aprovacao = timezone.now()
                saque.save()
        self.message_user(request, "Saques selecionados foram aprovados com sucesso.")
    approve_saques.short_description = "Aprovar Saques Selecionados"

    def reject_saques(self, request, queryset):
        queryset.update(status='rejeitado')
        self.message_user(request, "Saques selecionados foram rejeitados.")
    reject_saques.short_description = "Rejeitar Saques Selecionados"

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

# 9. Personaliza o Admin para o modelo ConfiguracaoPlataforma
class ConfiguracaoPlataformaAdmin(admin.ModelAdmin):
    list_display = ('whatsapp_numero', 'telegram_numero', 'whatsapp_grupo_link', 'telegram_grupo_link')
    def has_add_permission(self, request):
        from .models import ConfiguracaoPlataforma # Importa localmente para evitar circular import
        return not ConfiguracaoPlataforma.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return True 

# Registre seus modelos com as classes Admin personalizadas
admin.site.register(User, UserAdmin)
admin.site.register(SaldoUsuario, SaldoUsuarioAdmin)
admin.site.register(Nivel, NivelAdmin)
admin.site.register(Deposito, DepositoAdmin)
admin.site.register(Saque, SaqueAdmin)
admin.site.register(TarefaGanho, TarefaGanhoAdmin)
admin.site.register(Convite, ConviteAdmin)
admin.site.register(CoordenadaBancaria, CoordenadaBancariaAdmin)
admin.site.register(ConfiguracaoPlataforma, ConfiguracaoPlataformaAdmin)
