# pedido/views.py - Arquivo completo

from django.shortcuts import render, redirect, reverse
from django.views.generic import ListView, DetailView
from django.views import View
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from produto.models import Variacao
from produto.templatetags.omfilters import cart_total_qtd, cart_totals
from .models import Pedido, ItemPedido
import json
import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import datetime, timedelta
import uuid
import base64
import qrcode
from io import BytesIO
from django.utils import timezone
from mercadopago import SDK



# Configure o Stripe com sua chave secreta
stripe.api_key = settings.STRIPE_SECRET_KEY


class DispatchLoginRequiredMixin(View):
    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect('perfil:criar')

        return super().dispatch(*args, **kwargs)


class ProcessarPagamento(DispatchLoginRequiredMixin, View):
    """View para processar o pagamento via Stripe"""
    
    def post(self, request, *args, **kwargs):
        try:
            # Obtém o pedido
            pedido_id = kwargs.get('pk')
            pedido = Pedido.objects.get(pk=pedido_id, usuario=request.user)
            
            # Verifica se o pedido já foi pago
            if pedido.status != 'CR':
                messages.error(request, 'Este pedido já foi processado.')
                return redirect('pedido:detalhe', pk=pedido.pk)
            
            # Obtém o token do Stripe do formulário
            token = request.POST.get('stripeToken')
            
            if not token:
                messages.error(request, 'Token de pagamento não encontrado.')
                return redirect('pedido:pagar', pk=pedido.pk)
            
            try:
                # Cria o pagamento no Stripe
                charge = stripe.Charge.create(
                    amount=int(pedido.get_total_final() * 100),  # Valor em centavos
                    currency='brl',
                    description=f'Pedido #{pedido.pk} - {request.user.email}',
                    source=token,
                    metadata={
                        'pedido_id': pedido.pk,
                        'usuario_id': request.user.id,
                        'usuario_email': request.user.email
                    }
                )
                
                # Atualiza o status do pedido
                pedido.status = 'AP'  # Aprovado
                pedido.save()
                
                # Atualiza o estoque
                itens_pedido = ItemPedido.objects.filter(pedido=pedido)
                for item in itens_pedido:
                    variacao = Variacao.objects.get(id=item.variacao_id)
                    variacao.estoque -= item.quantidade
                    variacao.save()
                
                messages.success(
                    request,
                    f'Pagamento realizado com sucesso! Pedido #{pedido.pk} confirmado.'
                )
                
                return redirect('pedido:detalhe', pk=pedido.pk)
                
            except stripe.error.CardError as e:
                # Erro no cartão (cartão recusado, etc)
                messages.error(request, f'Erro no pagamento: {e.user_message}')
                return redirect('pedido:pagar', pk=pedido.pk)
                
            except stripe.error.StripeError as e:
                # Outros erros do Stripe
                messages.error(request, 'Erro ao processar pagamento. Tente novamente.')
                return redirect('pedido:pagar', pk=pedido.pk)
                
        except Pedido.DoesNotExist:
            messages.error(request, 'Pedido não encontrado.')
            return redirect('pedido:lista')
        
        except Exception as e:
            messages.error(request, f'Erro inesperado: {str(e)}')
            return redirect('pedido:pagar', pk=pedido_id)


class CriarIntentoPagamento(DispatchLoginRequiredMixin, View):
    """View para criar Payment Intent (método mais moderno do Stripe)"""
    
    def post(self, request, *args, **kwargs):
        try:
            pedido_id = kwargs.get('pk')
            pedido = Pedido.objects.get(pk=pedido_id, usuario=request.user)
            
            # Cria o Payment Intent
            intent = stripe.PaymentIntent.create(
                amount=int(pedido.get_total_final() * 100),
                currency='brl',
                metadata={
                    'pedido_id': pedido.pk,
                    'usuario_id': request.user.id
                }
            )
            
            return JsonResponse({
                'client_secret': intent.client_secret,
                'pedido_id': pedido.pk
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class WebhookStripe(View):
    """Webhook para receber notificações do Stripe"""
    
    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET  # Configure isso no settings.py
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError:
            return JsonResponse({'error': 'Invalid payload'}, status=400)
        except stripe.error.SignatureVerificationError:
            return JsonResponse({'error': 'Invalid signature'}, status=400)
        
        # Processa o evento
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            pedido_id = payment_intent['metadata']['pedido_id']
            
            try:
                pedido = Pedido.objects.get(pk=pedido_id)
                pedido.status = 'AP'
                pedido.save()
                
                # Atualiza estoque
                itens_pedido = ItemPedido.objects.filter(pedido=pedido)
                for item in itens_pedido:
                    variacao = Variacao.objects.get(id=item.variacao_id)
                    variacao.estoque -= item.quantidade
                    variacao.save()
                    
            except Pedido.DoesNotExist:
                pass
        
        return JsonResponse({'status': 'success'})


class Pagar(DispatchLoginRequiredMixin, DetailView):
    template_name = 'pedido/pagar.html'
    model = Pedido
    pk_url_kwarg = 'pk'
    context_object_name = 'pedido'

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        qs = qs.filter(usuario=self.request.user)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stripe_pub_key'] = settings.STRIPE_PUB_KEY
        return context


class SalvarPedido(View):
    template_name = 'pedido/pagar.html'

    def get(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            messages.error(
                self.request,
                'Você precisa fazer login.'
            )
            return redirect('perfil:criar')
        
        if not self.request.session.get('carrinho'):
            messages.error(
                self.request,
                'Carrinho vazio.'
            )
            return redirect('produto:lista')
        
        carrinho = self.request.session.get('carrinho')
        
        carrinho_variacao_ids = [v for v in carrinho]
        bd_variacoes = list(
            Variacao.objects.select_related('produto').filter(id__in=carrinho_variacao_ids)
        )

        for variacao in bd_variacoes:
            vid = str(variacao.id)

            estoque = variacao.estoque
            qtd_carrinho = carrinho[vid]['quantidade']
            preco_unt = carrinho[vid]['preco_unitario']
            preco_unt_promo = carrinho[vid]['preco_unitario_promocional']
            error_msg_estoque = ''

            if estoque < qtd_carrinho:
                carrinho[vid]['quantidade'] = estoque
                carrinho[vid]['preco_quantitativo'] = estoque * preco_unt
                carrinho[vid]['preco_quantitativo_promocional'] = estoque * preco_unt_promo

                error_msg_estoque = 'Estoque insuficiente para alguns produtos do seu carrinho. '\
                                    'Reduzimos a quantidade desses produtos. Por favor, verifique '\
                                    'no quais produtos foram afetados a seguir.'

            if error_msg_estoque:
                messages.error(
                    self.request,
                    error_msg_estoque
                )

                self.request.session.save()
                return redirect('produto:carrinho')
        
        qtd_total_carrinho = cart_total_qtd(carrinho)
        valor_total_carrinho = cart_totals(carrinho)

        # Cria o pedido com o total original (sem desconto)
        pedido = Pedido(
            usuario=self.request.user,
            total=valor_total_carrinho,  # Total sem desconto
            qtd_total=qtd_total_carrinho,
            status='CR',
        )

        # Aplica o cupom se existir na sessão
        if 'cupom' in self.request.session:
            pedido.aplicar_cupom_da_sessao(self.request.session['cupom'])
            
        # Salva o pedido (com desconto aplicado se houver)
        pedido.save()

        # Cria os itens do pedido
        ItemPedido.objects.bulk_create(
            [
                ItemPedido(
                    pedido=pedido,
                    produto=v['produto_nome'],
                    produto_id=v['produto_id'],
                    variacao=v['variacao_nome'],
                    variacao_id=v['variacao_id'],
                    preco=v['preco_quantitativo'],
                    preco_promocional=v['preco_quantitativo_promocional'],
                    quantidade=v['quantidade'],
                    imagem=v['imagem'],
                ) for v in carrinho.values()
            ]
        )

        # Limpa o carrinho e o cupom da sessão
        del self.request.session['carrinho']
        if 'cupom' in self.request.session:
            del self.request.session['cupom']
            
        self.request.session.save()
        
        # Se houve desconto aplicado, mostra mensagem de sucesso
        if pedido.cupom:
            messages.success(
                self.request,
                f'Pedido criado com sucesso! Cupom {pedido.cupom.codigo} aplicado. '
                f'Desconto de R$ {pedido.desconto:.2f}'
            )
        
        return redirect(
            reverse(
                'pedido:pagar',
                kwargs={
                    'pk': pedido.pk
                }
            )
        )


class Detalhe(DispatchLoginRequiredMixin, DetailView):
    model = Pedido
    context_object_name = 'pedido'
    template_name = 'pedido/detalhe.html'
    pk_url_kwarg = 'pk'
    
    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        qs = qs.filter(usuario=self.request.user)
        return qs


class Lista(DispatchLoginRequiredMixin, ListView):
    model = Pedido
    context_object_name = 'pedidos'
    template_name = 'pedido/lista.html'
    paginate_by = 10
    ordering = ['-id']
    
    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        qs = qs.filter(usuario=self.request.user)
        return qs


def teste_stripe(request):
    """View de teste do Stripe - pode remover em produção"""
    return render(request, 'teste_stripe.html')


class ProcessarPagamentoPix(DispatchLoginRequiredMixin, View):
    """View para processar pagamento via PIX com QR Code REAL - Versão Corrigida"""
    
    def gerar_pix_payload(self, chave, nome, cidade, valor, txid):
        """Gera o payload PIX manualmente"""
        # Payload Format Indicator
        payload = "000201"
        
        # Merchant Account Information
        if '@' in chave:  # Email
            gui = "0014BR.GOV.BCB.PIX0136" + chave
        elif '+' in chave:  # Telefone
            gui = "0014BR.GOV.BCB.PIX0115" + chave.replace('+', '')
        elif len(chave) == 11:  # CPF
            gui = "0014BR.GOV.BCB.PIX0111" + chave
        else:  # Chave aleatória
            gui = "0014BR.GOV.BCB.PIX0136" + chave
            
        payload += "26" + str(len(gui)).zfill(2) + gui
        
        # Merchant Category Code
        payload += "52040000"
        
        # Transaction Currency (986 = BRL)
        payload += "5303986"
        
        # Transaction Amount
        if valor > 0:
            valor_str = "{:.2f}".format(valor)
            payload += "54" + str(len(valor_str)).zfill(2) + valor_str
        
        # Country Code
        payload += "5802BR"
        
        # Merchant Name
        nome_clean = nome[:25].upper()
        payload += "59" + str(len(nome_clean)).zfill(2) + nome_clean
        
        # Merchant City
        cidade_clean = cidade[:15].upper()
        payload += "60" + str(len(cidade_clean)).zfill(2) + cidade_clean
        
        # Additional Data Field Template
        if txid:
            txid_clean = txid[:25]
            adicional = "05" + str(len(txid_clean)).zfill(2) + txid_clean
            payload += "62" + str(len(adicional)).zfill(2) + adicional
        
        # CRC16 Placeholder
        payload += "6304"
        
        # Calcular CRC16
        crc = self.crc16(payload)
        payload += crc.upper()
        
        return payload
    
    def crc16(self, payload):
        """Calcula o CRC16 do payload"""
        crc = 0xFFFF
        polynomial = 0x1021
        
        for byte in payload.encode('utf-8'):
            crc ^= byte << 8
            
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ polynomial
                else:
                    crc = crc << 1
                    
            crc &= 0xFFFF
            
        return format(crc, '04X')
    
    def post(self, request, *args, **kwargs):
        try:
            pedido_id = kwargs.get('pk')
            pedido = Pedido.objects.get(pk=pedido_id, usuario=request.user)
            
            if pedido.status != 'CR':
                messages.error(request, 'Este pedido já foi processado.')
                return redirect('pedido:detalhe', pk=pedido.pk)
            
            # Configurações do PIX
            chave_pix = "cafe.bela.esperanca@email.com"  # Sua chave PIX
            nome_recebedor = "CAFE BELA ESPERANCA"
            cidade_recebedor = "MANDAGUARI"
            valor = float(pedido.get_total_final())
            txid = "PEDIDO{:06d}".format(pedido.pk)
            
            # Gerar payload PIX
            pix_code = self.gerar_pix_payload(
                chave=chave_pix,
                nome=nome_recebedor,
                cidade=cidade_recebedor,
                valor=valor,
                txid=txid
            )
            
            # Gerar QR Code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(pix_code)
            qr.make(fit=True)
            
            # Criar imagem
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Converter para base64
            buffer = BytesIO()
            img.save(buffer, 'PNG')
            buffer.seek(0)
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Salvar referência
            pedido.payment_intent_id = "PIX_{}_{}_{}".format(
                pedido.pk, 
                datetime.now().strftime('%Y%m%d%H%M%S'),
                uuid.uuid4().hex[:8]
            )
            pedido.status = 'PP'
            pedido.save()
            
            context = {
                'pedido': pedido,
                'pix_code': pix_code,
                'qr_code_image': qr_code_base64,
                'payment_intent_id': pedido.payment_intent_id,
                'expira_em': 30,
                'chave_pix': chave_pix,
                'nome_recebedor': nome_recebedor,
                'valor': valor
            }
            
            messages.success(request, 'QR Code PIX gerado com sucesso!')
            return render(request, 'pedido/pix_qrcode.html', context)
            
        except Exception as e:
            messages.error(request, 'Erro ao processar PIX: {}'.format(str(e)))
            return redirect('pedido:pagar', pk=pedido_id)

class PixQRCode(DispatchLoginRequiredMixin, View):
    """View para exibir QR Code do PIX"""
    
    def get(self, request, *args, **kwargs):
        try:
            pedido = Pedido.objects.get(pk=kwargs.get('pk'), usuario=request.user)
            
            if not pedido.payment_intent_id or not pedido.payment_intent_id.startswith('PIX_'):
                messages.error(request, 'Informações de pagamento PIX não encontradas.')
                return redirect('pedido:pagar', pk=pedido.pk)
            
            # Gerar código PIX novamente (simulado)
            pix_code = f"00020126580014BR.GOV.BCB.PIX0136{uuid.uuid4()}"
            pix_code += f"52040000530398654{pedido.get_total_final():.2f}"
            pix_code += f"5802BR5925CAFE BELA ESPERANCA6009SAO PAULO"
            pix_code += f"62{pedido.pk:06d}63045C7B"
            
            qr_code_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="  # Placeholder
            
            context = {
                'pedido': pedido,
                'pix_code': pix_code,
                'qr_code_image': qr_code_image,
                'payment_intent_id': pedido.payment_intent_id,
                'expira_em': 30
            }
            
            return render(request, 'pedido/pix_qrcode.html', context)
            
        except Exception as e:
            messages.error(request, f'Erro ao gerar QR Code: {str(e)}')
            return redirect('pedido:pagar', pk=kwargs.get('pk'))




class ProcessarPagamentoBoleto(View):
    def post(self, request, *args, **kwargs):
        try:
            pedido_id = kwargs.get('pk')
            pedido = Pedido.objects.get(pk=pedido_id, usuario=request.user)

            if pedido.status != 'CR':
                messages.error(request, 'Este pedido já foi processado.')
                return redirect('pedido:detalhe', pk=pedido.pk)

            # Inicializando o SDK do Mercado Pago
            mp = SDK(access_token=settings.MERCADOPAGO_ACCESS_TOKEN)

            # Criando a preferência de pagamento
            preference_data = {
                "items": [{
                    "title": f"Pedido #{pedido.id}",
                    "quantity": pedido.qtd_total,
                    "unit_price": float(pedido.get_total_final_decimal()),
                    "currency_id": "BRL",
                    "description": f"Pagamento do Pedido #{pedido.id}"
                }],
                "payer": {
                    "name": request.user.get_full_name(),
                    "email": request.user.email,
                },
                "payment_methods": {
                    "excluded_payment_types": [],
                    "installments": 1,
                    "excluded_payment_methods": [],
                    "default_payment_method_id": None,
                },
                "back_urls": {
                    "success": request.build_absolute_uri(reverse('pedido:detalhe', kwargs={'pk': pedido.pk})),
                    "failure": request.build_absolute_uri(reverse('pedido:pagar', kwargs={'pk': pedido.pk})),
                    "pending": request.build_absolute_uri(reverse('pedido:pagar', kwargs={'pk': pedido.pk})),
                },
                "auto_return": "approved",
            }

            preference_response = mp.preference().create(preference_data)
            preference = preference_response["response"]

            # Atualizando o status do pedido e salvando o ID da preferência
            pedido.payment_intent_id = preference["id"]
            pedido.status = 'PP'  # Pagamento Pendente
            pedido.save()

            # Redirecionando para a página de visualização do boleto
            return redirect('pedido:boleto_visualizar', pk=pedido.pk)

        except Pedido.DoesNotExist:
            messages.error(request, 'Pedido não encontrado.')
            return redirect('pedido:lista')

        except Exception as e:
            messages.error(request, f'Erro ao processar boleto: {str(e)}')
            return redirect('pedido:pagar', pk=pedido_id)

# Adicionar esta view para visualizar o boleto real
class BoletoVizualizar(DispatchLoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            pedido_id = kwargs.get('pk')
            pedido = Pedido.objects.get(pk=pedido_id, usuario=request.user)

            if not pedido.payment_intent_id:
                messages.error(request, 'Informações de pagamento não encontradas.')
                return redirect('pedido:pagar', pk=pedido.pk)

            # Inicializando o SDK do Mercado Pago
            mp = SDK(access_token=settings.MERCADOPAGO_ACCESS_TOKEN)

            # Buscando a preferência de pagamento
            preference = mp.preference().get(pedido.payment_intent_id)
            
            # A URL para pagamento deve estar dentro da resposta da preferência
            boleto_url = preference['response']['init_point']

            context = {
                'pedido': pedido,
                'boleto_url': boleto_url,
            }

            return render(request, 'pedido/boleto_vizualizar.html', context)

        except Pedido.DoesNotExist:
            messages.error(request, 'Pedido não encontrado.')
            return redirect('pedido:lista')

        except Exception as e:
            messages.error(request, f'Erro ao visualizar boleto: {str(e)}')
            return redirect('pedido:pagar', pk=kwargs.get('pk'))
        

class VerificarStatusPagamento(View):
    """API para verificar status do pagamento (PIX/Boleto)"""
    
    def get(self, request, *args, **kwargs):
        payment_intent_id = request.GET.get('payment_intent_id')
        
        if not payment_intent_id:
            return JsonResponse({'error': 'ID do pagamento não fornecido'}, status=400)
        
        try:
            # Buscar o pedido
            pedido = Pedido.objects.filter(payment_intent_id=payment_intent_id).first()
            
            if pedido:
                # Simular aprovação automática para teste
                if pedido.status == 'PP':  # Se está pendente
                    # Usar timezone.now() em vez de datetime.now()
                    tempo_decorrido = (timezone.now() - pedido.criado).total_seconds()
                    
                    # Aprovar após 10 segundos para teste
                    if tempo_decorrido > 10:
                        pedido.status = 'AP'
                        pedido.save()
                        
                        # Atualizar estoque
                        itens_pedido = ItemPedido.objects.filter(pedido=pedido)
                        for item in itens_pedido:
                            try:
                                variacao = Variacao.objects.get(id=item.variacao_id)
                                if variacao.estoque >= item.quantidade:
                                    variacao.estoque -= item.quantidade
                                    variacao.save()
                            except Variacao.DoesNotExist:
                                continue
                
                # Retornar status atual
                return JsonResponse({
                    'status': 'succeeded' if pedido.status == 'AP' else 'pending',
                    'amount': float(pedido.get_total_final()),
                    'currency': 'brl',
                    'pedido_status': pedido.status,
                    'pedido_id': pedido.pk
                })
            else:
                return JsonResponse({
                    'error': 'Pedido não encontrado',
                    'payment_intent_id': payment_intent_id
                }, status=404)
            
        except Exception as e:
            import traceback
            return JsonResponse({
                'error': str(e),
                'traceback': traceback.format_exc()
            }, status=500)