# core/signals.py (Atualizado com saldo_subsidy - Apenas a adição necessária)

from django.db.models.signals import post_save
from django.dispatch import receiver
# Embora signals não lidem diretamente com request/messages, pode ser útil para logs
# from django.contrib import messages 
from django.utils import timezone
from decimal import Decimal

from .models import Deposito, SaldoUsuario, Convite, Nivel, User # Importe Nivel e User também, caso precise.

@receiver(post_save, sender=Deposito)
def handle_deposit_approval(sender, instance, created, **kwargs):
    """
    Este signal é acionado toda vez que um objeto Deposito é salvo.
    Ele verifica se o depósito foi aprovado e se o convidado ativou um nível
    para conceder um subsídio ao convidante.
    """
    
    # Apenas age em depósitos existentes que foram 'aprovados'
    # e se o status realmente mudou para 'aprovado' (se não foi criado agora)
    if not created and instance.status == 'aprovado':
        user_depositante = instance.usuario
        valor_deposito = instance.valor
        nivel_ativar = instance.nivel_ativar

        # Verifica se o depósito aprovado ativou um nível
        if nivel_ativar:
            try:
                user_saldo = SaldoUsuario.objects.get(usuario=user_depositante)

                # Atualiza o saldo do usuário com o valor do depósito e ativa o nível
                # Apenas ativa se o nível for diferente OU se não houver nível ativo
                if user_saldo.nivel_ativo != nivel_ativar or user_saldo.nivel_ativo is None: 
                    user_saldo.nivel_ativo = nivel_ativar
                    user_saldo.data_ativacao_nivel = timezone.now()
                    user_saldo.total_depositado += valor_deposito # Acumula o valor depositado
                    user_saldo.ultimo_deposito_aprovado = timezone.now()
                    user_saldo.saldo_acumulado += valor_deposito # Adiciona o valor ao saldo acumulado
                    user_saldo.save()
                    print(f"DEBUG: Nível {nivel_ativar.nome} ativado para {user_depositante.phone_number}. Saldo atualizado para {user_saldo.saldo_acumulado}")

                    # Lógica para conceder o subsídio ao convidante
                    if user_depositante.referred_by: # Verifica se este usuário foi convidado por alguém
                        convidante = user_depositante.referred_by
                        
                        try:
                            # Busca o objeto Convite específico entre o convidante e o convidado
                            convite = Convite.objects.get(convidante=convidante, convidado=user_depositante)
                            
                            if not convite.subsidy_granted: # Verifica se o subsídio ainda não foi concedido
                                convidante_saldo = SaldoUsuario.objects.get(usuario=convidante)
                                SUBSIDIO_VALOR = Decimal('1000.00') # Valor do subsídio

                                # ***** ÚNICA ADIÇÃO NECESSÁRIA AQUI *****
                                convidante_saldo.saldo_subsidy += SUBSIDIO_VALOR # Adiciona ao saldo de subsídio
                                # ****************************************

                                convidante_saldo.saldo_acumulado += SUBSIDIO_VALOR # Mantém no saldo acumulado
                                convidante_saldo.save()
                                
                                convite.subsidy_granted = True # Marca o subsídio como concedido
                                convite.save()
                                print(f"DEBUG: Subsídio de {SUBSIDIO_VALOR} Kz concedido a {convidante.phone_number} por {user_depositante.phone_number} ativar nível. Saldo de subsídio e acumulado atualizados.")
                            else:
                                print(f"DEBUG: Subsídio para {user_depositante.phone_number} já concedido ao convidante {convidante.phone_number}.")

                        except Convite.DoesNotExist:
                            print(f"AVISO: Convite não encontrado para {user_depositante.phone_number} convidado por {convidante.phone_number}. Subsídio não concedido.")
                        except SaldoUsuario.DoesNotExist:
                            print(f"ERRO: SaldoUsuario do convidante {convidante.phone_number} não encontrado para conceder subsídio.")
                elif user_saldo.nivel_ativo is None: # Se não tinha nível ativo e não foi ativado agora
                    user_saldo.total_depositado += valor_deposito # Acumula o valor depositado
                    user_saldo.ultimo_deposito_aprovado = timezone.now()
                    user_saldo.saldo_acumulado += valor_deposito # Adiciona o valor ao saldo acumulado
                    user_saldo.save()
                    print(f"DEBUG: Depósito aprovado para {user_depositante.phone_number}, mas nenhum nível ativado. Saldo atualizado para {user_saldo.saldo_acumulado}")
            except SaldoUsuario.DoesNotExist:
                print(f"ERRO: SaldoUsuario para o usuário {user_depositante.phone_number} não encontrado ao aprovar depósito.")
        else:
            # Caso o depósito seja aprovado, mas não tenha um nivel_ativar associado (apenas para somar ao total depositado e acumulado)
            try:
                user_saldo = SaldoUsuario.objects.get(usuario=user_depositante)
                user_saldo.total_depositado += valor_deposito
                user_saldo.ultimo_deposito_aprovado = timezone.now()
                user_saldo.saldo_acumulado += valor_deposito
                user_saldo.save()
                print(f"DEBUG: Depósito de {valor_deposito} Kz aprovado para {user_depositante.phone_number}. Saldo atualizado para {user_saldo.saldo_acumulado}.")
            except SaldoUsuario.DoesNotExist:
                print(f"ERRO: SaldoUsuario para o usuário {user_depositante.phone_number} não encontrado ao aprovar depósito sem nível.")
                