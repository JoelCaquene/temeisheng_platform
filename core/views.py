# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.contrib.auth.views import PasswordChangeView, PasswordResetView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetCompleteView
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta, time
import random # Para simular a aprovação de depósito
# import hashlib # Este módulo não será mais necessário para gerar links de convite, pois o referral_code já é gerado no modelo User

from .forms import UserRegistrationForm, UserLoginForm, DepositoForm, SaqueForm, CustomPasswordChangeForm, CustomSetPasswordForm
from .models import User, SaldoUsuario, Nivel, Deposito, Saque, TarefaGanho, Convite, CoordenadaBancaria, ConfiguracaoPlataforma

# --- Views de Autenticação e Registro ---

def cadastro_view(request):
    if request.user.is_authenticated:
        return redirect('menu')

    # Alterado para buscar 'ref' (referral code) em vez de 'convidante' (phone_number)
    referral_code_from_url = request.GET.get('ref') 
    inviter_user = None
    if referral_code_from_url:
        try:
            # Tenta encontrar o usuário pelo referral_code
            inviter_user = User.objects.get(referral_code=referral_code_from_url)
        except User.DoesNotExist:
            messages.warning(request, "Código de convite inválido. Cadastrado sem vínculo.")

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False) # Não salva ainda para poder setar o referred_by
            
            # Lógica para associar o convidado ao convidante usando o campo referred_by do User
            if inviter_user:
                user.referred_by = inviter_user # Define quem convidou este usuário
                messages.info(request, f"Você foi cadastrado como convidado de {inviter_user.phone_number}.")
            
            user.save() # Agora salva o usuário com o referred_by

            # Criar o registro de Convite (para histórico e controle de subsídio). 
            # Isso ainda é necessário para o campo `subsidy_granted` e `data_convite`.
            if inviter_user:
                Convite.objects.create(convidante=inviter_user, convidado=user)
            
            # Inicializar SaldoUsuario para o novo usuário
            SaldoUsuario.objects.create(usuario=user)

            messages.success(request, 'Cadastro realizado com sucesso! Faça login para continuar.')
            return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        messages.error(request, f'{form.fields[field].label}: {error}')
    else:
        initial_data = {}
        if referral_code_from_url:
            # Você pode usar initial_data para preencher um campo oculto ou apenas para referência no template
            initial_data['referral_code_display'] = referral_code_from_url 
        form = UserRegistrationForm(initial=initial_data)
        
    return render(request, 'core/cadastro.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('menu')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=phone_number, password=password) 
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Bem-vindo(a) de volta, {user.first_name if user.first_name else user.phone_number}!')
                return redirect('menu')
            else:
                messages.error(request, 'Número de telefone ou senha inválidos.')
        else:
            messages.error(request, 'Por favor, insira seu número de telefone e senha.')
    else:
        form = UserLoginForm()
    return render(request, 'core/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'Você foi desconectado(a).')
    return redirect('login')

# --- Views da Plataforma (Após Login) ---

@login_required
def menu_view(request):
    saldo_usuario, created = SaldoUsuario.objects.get_or_create(usuario=request.user)
    if created:
        messages.info(request, "Seu saldo de usuário foi inicializado.")

    context = {
        'saldo': saldo_usuario, # Passa o objeto SaldoUsuario completo
        'username': request.user.phone_number,
        'niveis_disponiveis': Nivel.objects.filter(is_active=True).order_by('deposito_minimo'),
    }
    return render(request, 'core/menu.html', context)

@login_required
def deposito_view(request):
    coordenadas_bancarias = CoordenadaBancaria.objects.filter(is_active=True)
    niveis_disponiveis = Nivel.objects.filter(is_active=True).order_by('deposito_minimo')

    if request.method == 'POST':
        form = DepositoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    deposito = form.save(commit=False)
                    deposito.usuario = request.user
                    # O form já está preenchendo coordenada_bancaria_usada e nivel_ativar
                    deposito.save() # Salva o depósito. A aprovação e o subsídio serão tratados via signal.

                    messages.success(request, 'Seu pedido de depósito foi enviado com sucesso! Será aprovado em 5-15 minutos.')
                    return redirect('menu')
            except Exception as e:
                messages.error(request, f'Erro ao enviar o pedido de depósito: {e}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        messages.error(request, f'{form.fields[field].label}: {error}')
    else:
        form = DepositoForm()

    context = {
        'form': form,
        'coordenadas_bancarias': coordenadas_bancarias,
        'niveis_disponiveis': niveis_disponiveis, # Passa para o template caso queira exibir fora do form
    }
    return render(request, 'core/deposito.html', context)

@login_required
def saque_view(request):
    user_saldo = get_object_or_404(SaldoUsuario, usuario=request.user)
    saques_recentes = Saque.objects.filter(usuario=request.user).order_by('-data_solicitacao')[:5]

    # Puxa os dados bancários do SaldoUsuario (assumindo que você já adicionou banco_padrao_saque e iban_padrao_saque lá)
    banco_cliente_saque = user_saldo.banco_padrao_saque 
    iban_cliente_saque = user_saldo.iban_padrao_saque 

    # Alternativa: Puxar do último saque aprovado se o SaldoUsuario não tiver esses campos preenchidos
    if not banco_cliente_saque and not iban_cliente_saque:
        last_approved_saque = Saque.objects.filter(usuario=request.user, aprovado=True).order_by('-data_aprovacao').first()
        if last_approved_saque:
            banco_cliente_saque = last_approved_saque.nome_banco_cliente
            iban_cliente_saque = last_approved_saque.iban_cliente

    if request.method == 'POST':
        form = SaqueForm(request.POST) 
        if form.is_valid():
            valor_saque = form.cleaned_data['valor']
            
            # Validações de saldo mínimo e horas
            if user_saldo.saldo_acumulado < valor_saque:
                messages.error(request, 'Saldo insuficiente para realizar este saque.')
                return redirect('saque')
            
            if valor_saque < 1500:
                messages.error(request, 'O valor mínimo para saque é de 1500 Kz.')
                return redirect('saque')

            today = timezone.localdate()
            saque_hoje = Saque.objects.filter(usuario=request.user, data_solicitacao__date=today, aprovado=False).exists()
            if saque_hoje:
                messages.warning(request, 'Você já tem um saque pendente hoje. Aguarde a aprovação do saque anterior.')
                return redirect('saque')
            
            luanda_tz = timezone.get_fixed_timezone(timedelta(hours=1)) 
            now_luanda = timezone.localtime(timezone.now(), timezone=luanda_tz)
            
            is_weekday_or_saturday = now_luanda.weekday() < 6 # 0=Segunda, 5=Sábado
            is_within_hours = time(9,0) <= now_luanda.time() <= time(18,0)

            if not (is_weekday_or_saturday and is_within_hours):
                messages.warning(request, 'Saques são permitidos apenas de Segunda a Sábado, das 09:00h às 18:00h (Horário de Angola).')
                return redirect('saque')

            try:
                with transaction.atomic():
                    saque = form.save(commit=False)
                    saque.usuario = request.user
                    # Atribui os dados bancários puxados do perfil (ou último saque aprovado)
                    saque.nome_banco_cliente = banco_cliente_saque
                    saque.iban_cliente = iban_cliente_saque
                    saque.save()

                    user_saldo.saldo_acumulado -= valor_saque
                    user_saldo.total_sacado += valor_saque
                    user_saldo.ultimo_saque_solicitado = timezone.now()
                    user_saldo.save()

                    messages.success(request, 'Seu pedido de saque foi enviado com sucesso e está em processamento.')
                    return redirect('saque')
            except Exception as e:
                messages.error(request, f'Erro ao solicitar o saque: {e}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        messages.error(request, f'{form.fields[field].label}: {error}')
    else:
        form = SaqueForm()

    context = {
        'saldo': user_saldo,
        'form': form,
        'saques_recentes': saques_recentes,
        'banco_cliente_saque': banco_cliente_saque,
        'iban_cliente_saque': iban_cliente_saque,
        'last_saque_data': Saque.objects.filter(usuario=request.user, aprovado=True).order_by('-data_aprovacao').first(),
    }
    return render(request, 'core/saque.html', context)

@login_required
def tarefa_view(request):
    user_saldo = get_object_or_404(SaldoUsuario, usuario=request.user)
    
    today = timezone.localdate()
    tarefa_hoje_realizada = TarefaGanho.objects.filter(usuario=request.user, data_ganho=today).exists()

    if request.method == 'POST':
        if user_saldo.nivel_ativo:
            if not tarefa_hoje_realizada:
                ganho_do_dia = user_saldo.nivel_ativo.ganho_diario
                
                try:
                    with transaction.atomic():
                        TarefaGanho.objects.create(
                            usuario=request.user,
                            nivel=user_saldo.nivel_ativo,
                            valor_ganho=ganho_do_dia,
                            data_ganho=today
                        )
                        user_saldo.saldo_acumulado += ganho_do_dia
                        user_saldo.save()
                        messages.success(request, f'Parabéns! Você ganhou {ganho_do_dia} Kz na sua tarefa diária.')
                except Exception as e:
                    messages.error(request, f'Erro ao registrar o ganho da tarefa: {e}')
                return redirect('tarefa')
            else:
                messages.info(request, 'Você já realizou sua tarefa diária. Volte amanhã para mais ganhos!')
        else:
             messages.warning(request, 'Você precisa ter um nível ativo para realizar tarefas e ganhar. Faça um depósito para ativar seu nível.')
    
    context = {
        'saldo': user_saldo,
        'tarefa_hoje_realizada': tarefa_hoje_realizada,
        'ganho_diario_estimado': user_saldo.nivel_ativo.ganho_diario if user_saldo.nivel_ativo else 0,
    }
    return render(request, 'core/tarefa.html', context)

@login_required
def nivel_view(request):
    niveis = Nivel.objects.filter(is_active=True).order_by('deposito_minimo')
    user_saldo = get_object_or_404(SaldoUsuario, usuario=request.user)
    
    context = {
        'niveis': niveis,
        'nivel_ativo_usuario': user_saldo.nivel_ativo,
    }
    return render(request, 'core/nivel.html', context)

@login_required
def minha_equipe_view(request):
    # Usa o referral_code do usuário logado para gerar o link
    # Garante que o referral_code exista. Se não, ele será gerado na primeira chamada a save().
    if not request.user.referral_code:
        request.user.save() # Isso irá acionar o método save() no modelo User e gerar o referral_code se não existir
    
    link_convite = request.build_absolute_uri(reverse('cadastro') + f'?ref={request.user.referral_code}')

    # Puxa os usuários que foram referenciados por este usuário (diretamente do User.referred_users)
    # Usa select_related para otimizar queries e pegar dados de saldo e nível
    convidados_diretos = request.user.referred_users.all().select_related('saldo', 'saldo__nivel_ativo')
    
    equipe_detalhes = []
    for convidado_user in convidados_diretos:
        # Tenta encontrar o objeto Convite para pegar o 'data_convite' e 'subsidy_granted'
        # É importante ter o objeto Convite para esses campos específicos
        convite_obj = Convite.objects.filter(convidante=request.user, convidado=convidado_user).first()
        
        equipe_detalhes.append({
            'phone_number': convidado_user.phone_number,
            'first_name': convidado_user.first_name,
            'data_convite': convite_obj.data_convite if convite_obj else convidado_user.date_joined, # Fallback para data de registro se Convite não existir
            'nivel_ativo': convidado_user.saldo.nivel_ativo.nome if convidado_user.saldo and convidado_user.saldo.nivel_ativo else 'Nenhum',
            'tem_nivel_ativo': convidado_user.saldo.nivel_ativo is not None if convidado_user.saldo else False,
            'subsidy_granted': convite_obj.subsidy_granted if convite_obj else False,
        })
    
    context = {
        'link_convite': link_convite,
        'equipe_detalhes': equipe_detalhes,
        'total_convidados': convidados_diretos.count(), # Adicionado para exibir o total de convidados
    }
    return render(request, 'core/minha_equipe.html', context)

@login_required
def perfil_view(request):
    user_saldo = get_object_or_404(SaldoUsuario, usuario=request.user)
    
    context = {
        'user': request.user,
        'saldo': user_saldo, # Passa o objeto SaldoUsuario completo
        'last_saque': Saque.objects.filter(usuario=request.user, aprovado=True).order_by('-data_aprovacao').first(),
    }
    return render(request, 'core/perfil.html', context)

@login_required
def update_profile_view(request):
    user_saldo = get_object_or_404(SaldoUsuario, usuario=request.user) # Puxa o saldo do usuário

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        # Campos de banco e IBAN para serem editados no perfil
        # Certifique-se de que os nomes dos campos no seu HTML (input `name`) correspondem a estes
        banco_cliente = request.POST.get('banco_padrao_saque', '').strip() # Corrigido para nome esperado do campo no model
        iban_cliente = request.POST.get('iban_padrao_saque', '').strip()   # Corrigido para nome esperado do campo no model

        # Atualiza o nome
        if first_name:
            request.user.first_name = first_name
        else:
            request.user.first_name = '' # Permite limpar o nome
        
        # Atualiza os dados bancários no SaldoUsuario
        # Assumimos que 'banco_padrao_saque' e 'iban_padrao_saque' já foram adicionados ao modelo SaldoUsuario
        user_saldo.banco_padrao_saque = banco_cliente 
        user_saldo.iban_padrao_saque = iban_cliente   
        user_saldo.save() 

        request.user.save() 

        messages.success(request, 'Perfil atualizado com sucesso!')
        return redirect('perfil')

    context = {
        'user': request.user,
        'saldo': user_saldo, # Para preencher os campos de IBAN/Banco no form de edição
    }
    return render(request, 'core/update_profile.html', context)


class CustomPasswordChangeView(PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'core/alterar_senha.html'
    success_url = reverse_lazy('perfil')
    def form_valid(self, form):
        messages.success(self.request, 'Sua senha foi alterada com sucesso!')
        return super().form_valid(form)

class CustomPasswordResetView(PasswordResetView):
    template_name = 'core/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html' 
    subject_template_name = 'registration/password_reset_subject.txt' 
    success_url = reverse_lazy('password_reset_done')
    form_class = UserLoginForm 
    
    def post(self, request, *args, **kwargs):
        phone_number = request.POST.get('username')
        if phone_number:
            try:
                user_instance = User.objects.get(phone_number=phone_number)
                request.POST._mutable = True
                request.POST['email'] = f"{phone_number}@temeisheng.com" 
                request.POST._mutable = False
                
                response = super().post(request, *args, **kwargs)
                messages.info(request, "Se um número de telefone correspondente for encontrado, um link de redefinição de senha foi 'enviado'. (Verifique seu e-mail, se configurado, ou entre em contato com o suporte para redefinição por telefone).")
                return response
            except User.DoesNotExist:
                messages.error(request, 'Número de telefone não encontrado.')
                form = self.form_class(request.POST) 
                return render(request, self.template_name, {'form': form})
        else:
            messages.error(request, 'Por favor, forneça um número de telefone.')
            form = self.form_class(request.POST)
            return render(request, self.template_name, {'form': form})

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'core/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = 'core/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'core/password_reset_complete.html'

def sobre_view(request):
    context = {
        'titulo': "Sobre a TEMEISHENG",
        'introducao': "A TEMEISHENG é uma empresa de tecnologia que se destaca na fabricação de sistemas de áudio.",
        'resumo_historia': {
            'origem': "A TEMEISHENG foi fundada em 1999 na China, especificamente em Guangzhou.",
            'objetivo': "O principal objetivo da TEMEishENG é a concepção, fabricação e comercialização de sistemas de áudio, com foco em oferecer produtos de qualidade e satisfazer as necessidades dos clientes. Eles são conhecidos por sua expertise em caixas de som portáteis com bateria.",
        },
        'historia_angola': {
            'surgimento': "Nossa empresa em Angola surgiu em 21 de Julho de 2025.",
            'duracao_mercado': "Nossa empresa no campo de investimento online vai durar cerca de 5 anos.",
            'contrato_cliente': "Nossos contratos com os clientes serão de 1 ano. Após 1 ano, o cliente receberá seu dinheiro de ativação da conta. Se desejar continuar, deverá renovar o contrato.",
        }
    }
    try:
        config = ConfiguracaoPlataforma.objects.first()
        if config:
            context['whatsapp_numero'] = config.whatsapp_numero
            context['telegram_numero'] = config.telegram_numero
            context['whatsapp_grupo_link'] = config.whatsapp_grupo_link
            context['telegram_grupo_link'] = config.telegram_grupo_link
    except ConfiguracaoPlataforma.DoesNotExist:
        messages.warning(request, "Configurações da plataforma não encontradas.")
    
    return render(request, 'core/sobre.html', context)
    