# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

# 1. Gerenciador de Usuários Personalizado
class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('O número de telefone é obrigatório.')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(phone_number, password, **extra_fields)

# 2. Modelo de Usuário Personalizado
class User(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=15, unique=True, verbose_name="Número de Telefone")
    first_name = models.CharField(max_length=30, blank=True, verbose_name="Nome")
    last_name = models.CharField(max_length=150, blank=True, verbose_name="Sobrenome")
    date_joined = models.DateTimeField(default=timezone.now, verbose_name="Data de Registo")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    is_staff = models.BooleanField(default=False, verbose_name="Membro da Equipe") # Para acesso ao admin

    objects = UserManager()

    USERNAME_FIELD = 'phone_number' # Usaremos o número de telefone para login
    REQUIRED_FIELDS = [] # Nenhum campo adicional obrigatório para superuser

    def __str__(self):
        return self.phone_number

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

# 3. Modelo de Nível (editável pelo administrador)
class Nivel(models.Model):
    nome = models.CharField(max_length=50, unique=True, verbose_name="Nome do Nível")
    deposito_minimo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Depósito Mínimo") # Valor para ativar o nível
    ganho_diario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ganho Diário")
    ganho_mensal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ganho Mensal")
    ganho_anual = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Ganho Anual")
    ciclo_dias = models.IntegerField(verbose_name="Ciclo (dias)")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    def __str__(self):
        return f"{self.nome} (Depósito: {self.deposito_minimo} Kz)"

    class Meta:
        verbose_name = "Nível"
        verbose_name_plural = "Níveis"
        ordering = ['deposito_minimo'] # Ordenar por valor de depósito

# 4. Modelo de Coordenadas Bancárias (editável pelo administrador)
class CoordenadaBancaria(models.Model):
    nome_banco = models.CharField(max_length=100, unique=True, verbose_name="Nome do Banco")
    iban = models.CharField(max_length=34, unique=True, verbose_name="IBAN")
    nome_titular = models.CharField(max_length=100, verbose_name="Nome do Titular")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    def __str__(self):
        return f"{self.nome_banco} - {self.nome_titular}"

    class Meta:
        verbose_name = "Coordenada Bancária"
        verbose_name_plural = "Coordenadas Bancárias"

# 5. Modelo de Depósito
class Deposito(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='depositos', verbose_name="Usuário")
    nivel_ativar = models.ForeignKey(Nivel, on_delete=models.SET_NULL, null=True, verbose_name="Nível a Ativar")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Depositado")
    comprovativo = models.ImageField(upload_to='comprovativos_depositos/', verbose_name="Comprovativo")
    coordenada_bancaria_usada = models.ForeignKey(CoordenadaBancaria, on_delete=models.SET_NULL, null=True, blank=True, 
                                                    verbose_name="Coordenada Bancária Usada") # NOVO CAMPO
    data_solicitacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Solicitação")
    aprovado = models.BooleanField(default=False, verbose_name="Aprovado")
    data_aprovacao = models.DateTimeField(null=True, blank=True, verbose_name="Data de Aprovação")

    def __str__(self):
        status = "Aprovado" if self.aprovado else "Pendente"
        return f"Depósito de {self.usuario.phone_number} - {self.valor} Kz ({status})"

    class Meta:
        verbose_name = "Depósito"
        verbose_name_plural = "Depósitos"
        ordering = ['-data_solicitacao']

# 6. Modelo de Saque
class Saque(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saques', verbose_name="Usuário")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Solicitado")
    data_solicitacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Solicitação")
    aprovado = models.BooleanField(default=False, verbose_name="Aprovado")
    data_aprovacao = models.DateTimeField(null=True, blank=True, verbose_name="Data de Aprovação")
    # Campos para os dados bancários do usuário (para onde sacar) - Removidos daqui, agora no SaldoUsuario
    # nome_banco_cliente = models.CharField(max_length=100, blank=True, null=True, verbose_name="Banco do Cliente")
    # iban_cliente = models.CharField(max_length=34, blank=True, null=True, verbose_name="IBAN do Cliente")

    def __str__(self):
        status = "Aprovado" if self.aprovado else "Pendente"
        return f"Saque de {self.usuario.phone_number} - {self.valor} Kz ({status})"

    class Meta:
        verbose_name = "Saque"
        verbose_name_plural = "Saques"
        ordering = ['-data_solicitacao']

# 7. Modelo de Ganhos por Tarefa
class TarefaGanho(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ganhos_tarefa', verbose_name="Usuário")
    nivel = models.ForeignKey(Nivel, on_delete=models.SET_NULL, null=True, verbose_name="Nível no momento da tarefa")
    valor_ganho = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Ganho")
    data_ganho = models.DateField(auto_now_add=True, verbose_name="Data do Ganho")

    def __str__(self):
        return f"Ganho de tarefa para {self.usuario.phone_number} - {self.valor_ganho} Kz em {self.data_ganho}"

    class Meta:
        verbose_name = "Ganho de Tarefa"
        verbose_name_plural = "Ganhos de Tarefas"
        unique_together = ('usuario', 'data_ganho') # Garante 1 tarefa por dia por usuário
        ordering = ['-data_ganho']

# 8. Modelo de Convite (Equipa)
class Convite(models.Model):
    convidante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meus_convites', verbose_name="Convidante")
    convidado = models.OneToOneField(User, on_delete=models.CASCADE, related_name='convidado_por', verbose_name="Convidado")
    data_convite = models.DateTimeField(auto_now_add=True, verbose_name="Data do Convite")
    # NOVO CAMPO: Para controlar se o subsídio já foi concedido para este convite
    subsidy_granted = models.BooleanField(default=False, verbose_name="Subsídio Concedido")

    def __str__(self):
        return f"{self.convidante.phone_number} convidou {self.convidado.phone_number}"

    class Meta:
        verbose_name = "Convite"
        verbose_name_plural = "Convites"
        unique_together = ('convidante', 'convidado')


# 9. Modelo para Saldo do Usuário (para facilitar o controle de saldos)
class SaldoUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='saldo', verbose_name="Usuário")
    saldo_acumulado = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Saldo Acumulado")
    saldo_subsidio = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Saldo de Subsídio")
    total_sacado = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Total Sacado")
    nivel_ativo = models.ForeignKey(Nivel, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Nível Ativo")
    ultimo_deposito_aprovado_valor = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Último Depósito Aprovado")
    ultimo_saque_solicitado = models.DateTimeField(null=True, blank=True, verbose_name="Último Saque Solicitado") # Para controle de saque diário

    # NOVOS CAMPOS PARA DADOS BANCÁRIOS PADRÃO DO USUÁRIO
    banco_padrao_saque = models.CharField(max_length=100, blank=True, null=True, verbose_name="Banco Padrão para Saque")
    iban_padrao_saque = models.CharField(max_length=34, blank=True, null=True, verbose_name="IBAN Padrão para Saque")
    # FIM DOS NOVOS CAMPOS

    def __str__(self):
        return f"Saldo de {self.usuario.phone_number}"

    class Meta:
        verbose_name = "Saldo do Usuário"
        verbose_name_plural = "Saldos dos Usuários"


# 10. Modelo para Configurações da Plataforma (Whatsapp, Telegram, etc.)
class ConfiguracaoPlataforma(models.Model):
    whatsapp_numero = models.CharField(max_length=20, blank=True, null=True, verbose_name="Número de WhatsApp")
    telegram_numero = models.CharField(max_length=20, blank=True, null=True, verbose_name="Número de Telegram")
    whatsapp_grupo_link = models.URLField(max_length=200, blank=True, null=True, verbose_name="Link do Grupo de WhatsApp")
    telegram_grupo_link = models.URLField(max_length=200, blank=True, null=True, verbose_name="Link do Grupo de Telegram")

    class Meta:
        verbose_name = "Configuração da Plataforma"
        verbose_name_plural = "Configurações da Plataforma"

    def __str__(self):
        return "Configurações Gerais da Plataforma"

    # Restringe a apenas uma instância para este modelo
    def save(self, *args, **kwargs):
        if not self.pk and ConfiguracaoPlataforma.objects.exists():
            raise ValueError("Só pode haver uma instância de ConfiguracaoPlataforma.")
        return super(ConfiguracaoPlataforma, self).save(*args, **kwargs)
        