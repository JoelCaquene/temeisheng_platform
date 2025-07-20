# core/signals.py
from django.db.models.signals import post_save # Signal para após salvar um objeto
from django.dispatch import receiver # Decorador para registrar a função como recetor de um sinal
from django.utils import timezone # Para lidar com datas e horas
from datetime import timedelta # Para cálculos de tempo
from django.contrib import messages # Para enviar mensagens ao usuário (importante: Messages Framework)

from .models import Deposito, SaldoUsuario, Convite # Seus modelos

# Signal para lidar com a aprovação de depósitos
@receiver(post_save, sender=Deposito)
def handle_deposito_approval(sender, instance, created, **kwargs):
    # Esta função é executada sempre que um objeto Deposito é salvo.
    # 'created' é True se um novo objeto foi criado, False se foi atualizado.

    # Apenas processa se o depósito foi recém-criado e ainda não foi aprovado
    if created and not instance.aprovado:
        # Em um sistema de produção, esta lógica de "aprovação em 5-15 minutos"
        # seria implementada com tarefas assíncronas (ex: Celery, Django-RQ)
        # ou por um painel administrativo.
        # Para fins de demonstração, vamos simular a aprovação imediata aqui.

        instance.aprovado = True
        instance.data_aprovacao = timezone.now()
        instance.save(update_fields=['aprovado', 'data_aprovacao']) # Salva apenas os campos atualizados

        # Ativa o nível do usuário e atualiza o saldo
        user_saldo = SaldoUsuario.objects.get(usuario=instance.usuario)
        user_saldo.nivel_ativo = instance.nivel_ativar # Associa o nível ativado
        user_saldo.ultimo_deposito_aprovado_valor = instance.valor # Guarda o valor do depósito
        user_saldo.save()

        # Envia uma mensagem de sucesso para o usuário que fez o depósito
        # Note: messages.success funciona melhor em requisições HTTP. Para tarefas em background,
        # você precisaria de um sistema de notificações mais robusto.
        # Para o contexto de desenvolvimento, vamos assumir que o usuário estará logado e vendo esta mensagem.
        # Isso é uma simplificação para fins de demonstração.
        # messages.success(instance.usuario, f'Seu depósito de {instance.valor} Kz foi aprovado e seu nível {instance.nivel_ativar.nome} está ativo!')


# Signal para lidar com a atribuição de subsídio por convite
@receiver(post_save, sender=Convite)
def handle_convite_subsidy(sender, instance, created, **kwargs):
    # Esta função é executada sempre que um objeto Convite é salvo (ou seja, quando alguém é convidado).

    if created: # Apenas quando um novo convite é criado
        # O subsídio de 1000 Kz é dado ao convidante SE o convidado ativar um nível.
        # Neste signal, verificamos se o convidado JÁ TEM um nível ativo no momento do convite
        # ou se ele adquiriu um nível *após* o convite ser registrado.
        # A lógica atual do PDF diz "se a pessoa que convidares, ter um nível activo, vai receber um subsídio de 500 kz"
        # e "se a pessoa que ele convidar investir na plataforma, a pessoa que convidou vai receber subsídio automaticamente de 1000 kz".
        # Vamos usar a interpretação de 1000 Kz quando o convidado *investe/ativa um nível*.

        # Para simplificar o fluxo de sinais:
        # Assumimos que o Convite é criado quando o convidado se regista.
        # O subsídio é dado SE o convidado já tiver um nível ativo OU QUANDO ELE O ATIVAR.
        # Para este signal 'post_save' de Convite, vamos assumir que o subsídio é dado se o convidado *já tem* um nível ativo.
        # Se o subsídio deve ser dado SOMENTE quando o convidado *ATIVA* um nível, a lógica precisaria estar no `handle_deposito_approval`
        # ou num signal no SaldoUsuario para quando `nivel_ativo` muda.

        # Reinterpretando a lógica para 1000 Kz automaticamente quando o convidado **investir na plataforma** (ativar nível).
        # Esta lógica será melhor colocada NO SINAL DO DEPÓSITO OU NUM SIGNAL NO SALDOUSUARIO quando o nivel_ativo é definido.
        # Para manter a simplicidade AGORA, vamos usar o valor de 500 Kz quando o convidado É REGISTRADO (convite criado).
        # Mas, se a intenção é 1000 Kz APÓS ATIVAÇÃO DE NÍVEL, o código precisa ser movido.

        # REINTERPRETANDO para 1000 Kz no ato do convite *se o convidado JÁ ESTIVER ativo (o que não é comum)*,
        # OU mais logicamente, 1000 Kz quando o CONVIDADO ATIVA O NÍVEL.
        # Vamos refatorar isso para ser acionado quando o convidado *ATIVA* um nível.

        # Temporariamente, deixarei uma lógica simples que o subsídio de 500 Kz é dado
        # no momento do convite, independentemente do nível do convidado, para fins de demonstração,
        # mas isto pode ser ajustado para a lógica de 1000 Kz pós-ativação do convidado.

        # Lógica atual baseada em: "sempre que convidar alguém para se escrever com o seu link, se a pessoa que
        # [cite_start]convidares, ter um nível activo, vai receber um subsídio de 500 kz;" [cite: 58]
        # E também "se a pessoa que ele convidar investir na plataforma, a pessoa que convidou vai receber subsídio
        # [cite_start]automaticamente de 1000 kz" [cite: 31]
        # A contradição entre 500kz e 1000kz e o momento de atribuição (após registo/após investimento)
        # sugere que precisamos escolher uma interpretação.
        # Vamos optar por 1000 Kz quando o CONVIDADO ATIVA UM NÍVEL (que é o investimento).

        # VERIFICAÇÃO PARA SUBSÍDIO DE CONVITE (1000 Kz):
        # Esta lógica é mais adequada no signal `handle_deposito_approval` quando um usuário ativa um nível.
        # POR FAVOR, VEJA ONDE ESTA LÓGICA DEVERIA IR NO `handle_deposito_approval` (logo abaixo deste).

        pass # Por enquanto, este signal de Convite não fará a atribuição automática de 1000 Kz.
             # [cite_start]O subsídio será tratado no signal de Deposito, conforme a lógica do PDF[cite: 31].


# ATUALIZAÇÃO DO SINAL DE DEPÓSITO PARA INCLUIR O SUBSÍDIO DE CONVITE (1000 Kz)
@receiver(post_save, sender=Deposito)
def handle_deposito_and_subsidy(sender, instance, created, **kwargs):
    if created and instance.aprovado: # Apenas se o depósito foi criado E JÁ FOI APROVADO (pela linha anterior do signal)
        user_saldo = SaldoUsuario.objects.get(usuario=instance.usuario)

        # Lógica para ativar o nível do usuário
        user_saldo.nivel_ativo = instance.nivel_ativar
        user_saldo.ultimo_deposito_aprovado_valor = instance.valor
        user_saldo.save()
        messages.info(instance.usuario, f'Seu depósito de {instance.valor} Kz foi aprovado e seu nível {instance.nivel_ativar.nome} está ativo!')

        # [cite_start]Lógica de subsídio de convite (1000 Kz) [cite: 31]
        # Verifica se este usuário (o 'convidado') foi convidado por alguém
        try:
            convite_instance = Convite.objects.get(convidado=instance.usuario)
            convidante = convite_instance.convidante
            convidante_saldo = SaldoUsuario.objects.get(usuario=convidante)

            # Verifica se o subsídio já foi atribuído para este convite
            # Isso pode ser feito adicionando um campo 'subsidy_granted' ao modelo Convite
            # Ou verificando se o saldo do convidante já reflete o subsídio.
            # Por simplicidade, faremos uma verificação se o saldo de subsídio do convidante
            # não foi alterado pelo convidado antes. (Esta é uma simplificação, idealmente um campo no Convite seria melhor)
            # Para evitar atribuições múltiplas ao mesmo convite, adicionaremos um campo `subsidy_granted` no modelo Convite.

            # Para evitar erros AGORA, faremos uma verificação simples.
            # Se o subsídio já foi adicionado para este convite, não adicionar novamente.
            # Para isso, seria necessário adicionar um campo `subsidy_granted = models.BooleanField(default=False)` no modelo `Convite`.
            # Assumindo que você já o adicionou ao `Convite` e rodou `makemigrations` e `migrate`.

            # Se o convite ainda não teve o subsídio atribuído E o convidado ativou o nível
            if not convite_instance.subsidy_granted: # Assumindo que `subsidy_granted` existe no modelo Convite
                [cite_start]subsidio_valor = 1000 # Kz [cite: 31]
                convidante_saldo.saldo_acumulado += subsidio_valor
                convidante_saldo.saldo_subsidio += subsidio_valor
                convidante_saldo.save()
                convite_instance.subsidy_granted = True # Marca como concedido
                convite_instance.save(update_fields=['subsidy_granted'])
                messages.success(convidante, f'Parabéns! Você recebeu um subsídio de {subsidio_valor} Kz pelo convite de {instance.usuario.phone_number} que ativou o nível {instance.nivel_ativar.nome}.')

        except Convite.DoesNotExist:
            # O usuário não foi convidado por ninguém.
            pass
        except Exception as e:
            # Lidar com outros erros, se houver
            print(f"Erro ao atribuir subsídio: {e}")
            