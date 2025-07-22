# core/models.py

import uuid # Importar para gerar UUIDs para referral_code
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager # Importar BaseUserManager
from django.utils import timezone
from datetime import timedelta
from django.utils.translation import gettext_lazy as _ # Adicionado para mensagens de erro traduzíveis

# Campos para validação, se necessário (ex: para números de telefone)
from django.core.validators import RegexValidator

# NOVO: CustomUserManager para gerenciar a criação de usuários e superusuários
class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, email=None, password=None, **extra_fields):
        """
        Cria e salva um Usuário com o número de telefone e senha dados.
        """
        if not phone_number:
            raise ValueError(_('O número de telefone deve ser definido')) 
        
        # Garante que o email seja None se estiver vazio, ou normaliza
        email = self.normalize_email(email) if email else None 
        
        user = self.model(phone_number=phone_number, email=email, **extra_fields) 
        user.set_password(password) 
        user.save(using=self._db) 
        return user 

    def create_superuser(self, phone_number, email, password=None, **extra_fields):
        """
        Cria e salva um superusuário com o número de telefone e senha dados.
        """
        extra_fields.setdefault('is_staff', True) 
        extra_fields.setdefault('is_superuser', True) 
        extra_fields.setdefault('is_active', True) 

        if extra_fields.get('is_staff') is not True: 
            raise ValueError(_('Superuser deve ter is_staff=True.')) 
        if extra_fields.get('is_superuser') is not True: 
            raise ValueError(_('Superuser deve ter is_superuser=True.')) 
        
        # O campo 'email' é obrigatório para o superusuário neste método
        if not email: 
            raise ValueError(_('Superuser deve ter um endereço de email.')) 

        return self.create_user(phone_number, email, password, **extra_fields) 


class User(AbstractUser):
    # Alterado para usar phone_number como username_field
    username = None 
    phone_number_regex = RegexValidator(regex=r"^\+?1?\d{9,15}$", message="O número de telefone deve ser inserido no formato: '+999999999'. Até 15 dígitos permitidos.")
    phone_number = models.CharField(validators=[phone_number_regex], max_length=17, unique=True, verbose_name="Número de Telefone")
    
    # *** ESTA É A ÚNICA ALTERAÇÃO SIGNIFICATIVA PARA O SEU PROBLEMA DE CADASTRO ***
    # REMOVIDO unique=True. Isso permite que múltiplos usuários tenham email vazio ou null.
    email = models.EmailField(_("email address"), blank=True, null=True) 

    # Novo campo para o código de convite único
    referral_code = models.CharField(max_length=10, unique=True, blank=True, null=True, verbose_name="Código de Convite")
    # Campo para rastrear quem convidou este usuário
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_users', verbose_name="Convidado Por")

    USERNAME_FIELD = 'phone_number'
    # Ajustado REQUIRED_FIELDS: 'email' não é mais obrigatório para usuários normais, apenas para superusuários (via CustomUserManager).
    REQUIRED_FIELDS = ['first_name'] 

    # IMPORTANTE: Conecta o seu CustomUserManager ao seu modelo User
    objects = CustomUserManager() 

    def __str__(self):
        return self.phone_number

    # Sobrescreve o método save para garantir que o referral_code seja gerado
    def save(self, *args, **kwargs):
        if not self.referral_code:
            # Gera um código de convite único (ex: usando os primeiros caracteres de um UUID)
            self.referral_code = str(uuid.uuid4()).replace('-', '')[:10].upper()
            # Garante a unicidade caso haja colisão (improvável com UUID, mas boa prática)
            while User.objects.filter(referral_code=self.referral_code).exists():
                self.referral_code = str(uuid.uuid4()).replace('-', '')[:10].upper()
        super().save(*args, **kwargs)

class Nivel(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    deposito_minimo = models.DecimalField(max_digits=10, decimal_places=2)
    ganho_diario = models.DecimalField(max_digits=10, decimal_places=2)
    periodo_dias = models.IntegerField(default=365, help_text="Duração do nível em dias")
    is_active = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome

class SaldoUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='saldo')
    saldo_acumulado = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_depositado = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_sacado = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    nivel_ativo = models.ForeignKey(Nivel, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Nível Ativo Atual")
    data_ativacao_nivel = models.DateTimeField(null=True, blank=True, verbose_name="Data de Ativação do Nível")
    ultimo_deposito_aprovado = models.DateTimeField(null=True, blank=True, verbose_name="Último Depósito Aprovado")
    ultimo_saque_solicitado = models.DateTimeField(null=True, blank=True, verbose_name="Último Saque Solicitado")

    # NOVO CAMPO para o saldo de subsídio - max_digits 12 e decimal_places 2 para consistência
    saldo_subsidy = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Saldo de Subsídio de Convite")

    # Novos campos para armazenar os dados bancários padrão do usuário para saque
    banco_padrao_saque = models.CharField(max_length=100, blank=True, null=True, verbose_name="Banco Padrão para Saque")
    iban_padrao_saque = models.CharField(max_length=34, blank=True, null=True, verbose_name="IBAN Padrão para Saque")

    def __str__(self):
        return f"Saldo de {self.usuario.phone_number}"

    @property
    def proximo_ganho_disponivel(self):
        if self.nivel_ativo and self.data_ativacao_nivel:
            # Calcular a data de expiração do nível
            data_expiracao = self.data_ativacao_nivel + timedelta(days=self.nivel_ativo.periodo_dias)
            if timezone.now() < data_expiracao:
                return "Ativo"
            else:
                return "Expirado"
        return "N/A" # Sem nível ativo

    @property
    def nivel_expirado(self):
        if self.nivel_ativo and self.data_ativacao_nivel:
            data_expiracao = self.data_ativacao_nivel + timedelta(days=self.nivel_ativo.periodo_dias)
            return timezone.now() >= data_expiracao
        return False

class Deposito(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='depositos')
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    comprovante_pix = models.ImageField(upload_to='comprovantes_depositos/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)
    
    # Campos para registrar a coordenada bancária e o nível selecionado no momento do depósito
    coordenada_bancaria_usada = models.ForeignKey('CoordenadaBancaria', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Coordenada Bancária Usada")
    nivel_ativar = models.ForeignKey(Nivel, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Nível a Ativar")

    def __str__(self):
        return f"Depósito de {self.valor} por {self.usuario.phone_number} - Status: {self.status}"

class Saque(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saques')
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    nome_banco_cliente = models.CharField(max_length=100, verbose_name="Nome do Banco do Cliente")
    iban_cliente = models.CharField(max_length=34, verbose_name="IBAN do Cliente") # IBAN pode variar de tamanho, 34 é um bom limite
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Saque de {self.valor} por {self.usuario.phone_number} - Status: {self.status}"

class TarefaGanho(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tarefas_ganhas')
    nivel = models.ForeignKey(Nivel, on_delete=models.SET_NULL, null=True, blank=True)
    valor_ganho = models.DecimalField(max_digits=10, decimal_places=2)
    data_ganho = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Ganho de {self.valor_ganho} por {self.usuario.phone_number} em {self.data_ganho}"
    
    class Meta:
        unique_together = ('usuario', 'data_ganho') # Garante apenas 1 tarefa por dia por usuário

class Convite(models.Model):
    convidante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='convites_feitos')
    convidado = models.ForeignKey(User, on_delete=models.CASCADE, related_name='convites_recebidos')
    data_convite = models.DateTimeField(auto_now_add=True)
    # Novo campo para indicar se o subsídio já foi concedido para este convite específico
    subsidy_granted = models.BooleanField(default=False, verbose_name="Subsídio Concedido")

    def __str__(self):
        return f"{self.convidante.phone_number} convidou {self.convidado.phone_number}"
    
    class Meta:
        unique_together = ('convidante', 'convidado') 

class CoordenadaBancaria(models.Model):
    nome_banco = models.CharField(max_length=100)
    nome_titular = models.CharField(max_length=100)
    iban = models.CharField(max_length=34, unique=True)
    is_active = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome_banco} - {self.iban}"

class ConfiguracaoPlataforma(models.Model):
    whatsapp_numero = models.CharField(max_length=20, blank=True, null=True)
    telegram_numero = models.CharField(max_length=20, blank=True, null=True)
    whatsapp_grupo_link = models.URLField(max_length=500, blank=True, null=True)
    telegram_grupo_link = models.URLField(max_length=500, blank=True, null=True)

    class Meta:
        verbose_name = "Configuração da Plataforma"
        verbose_name_plural = "Configurações da Plataforma"
        unique_together = ('whatsapp_numero', 'telegram_numero') 

    def __str__(self):
        return "Configurações Gerais da Plataforma"

    def save(self, *args, **kwargs):
        # Garante que só exista uma instância
        if not self.pk and ConfiguracaoPlataforma.objects.exists():
            raise Exception("Já existe uma configuração de plataforma. Edite a existente.")
        super(ConfiguracaoPlataforma, self).save(*args, **kwargs)
        