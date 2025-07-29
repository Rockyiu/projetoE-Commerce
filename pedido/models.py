from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
# Certifique-se de que o app cupons foi criado antes de importar
from cupons.models import Cupom


class Pedido(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    total = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Total do pedido sem desconto"
    )  # Mudado de FloatField para DecimalField
    qtd_total = models.PositiveIntegerField()
    criado = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        default="CR",
        max_length=2,
        choices = (
            ('AP', 'Aprovado'),  # Mudei 'A' para 'AP' para evitar duplicação
            ('CR', 'Criado'),
            ('RP', 'Reprovado'),  # Mudei 'R' para 'RP' para evitar duplicação
            ('PP', 'Pagamento pendente'),  # Mudei 'P' para 'PP'
            ('FP', 'Falha no Pagamento'),  # Mudei 'F' para 'FP'
            ('PR', 'Processando'),  # Mudei 'P' para 'PR'
            ('RE', 'Reembolsado'),  # Mudei 'R' para 'RE'
            ('CO', 'Concluido'),
            ('CA', 'Cancelado'),  # Mudei 'C' para 'CA'
            ('EN', 'Enviado'),  # Mudei 'E' para 'EN'
            ('FI', 'Finalizado'),  # Mudei 'F' para 'FI'
        )
    )
    
    # Novos campos para cupom
    cupom = models.ForeignKey(
        Cupom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos'
    )
    desconto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Valor do desconto aplicado"
    )

    payment_intent_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="ID do Payment Intent do Stripe"
    )

    payment_id_mercadopago = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="ID do pagamento no MercadoPago"
    )
    
    def __str__(self):
        return f'Pedido N. {self.pk}'
    
    @property
    def total_com_desconto(self):
        """Retorna o total já com o desconto aplicado"""
        return self.total - self.desconto  # Agora ambos são Decimal
    
    def aplicar_cupom_da_sessao(self, session_cupom_data):
        """
        Aplica o cupom da sessão ao pedido
        Deve ser chamado antes de salvar o pedido
        """
        if session_cupom_data and 'id' in session_cupom_data:
            try:
                cupom = Cupom.objects.get(id=session_cupom_data['id'])
                if cupom.is_valido():
                    self.cupom = cupom
                    self.desconto = Decimal(str(session_cupom_data['desconto']))
                    # NÃO modifica o total original - mantém para histórico
                    # O desconto será aplicado quando chamar get_total_final()
                    
                    # Incrementa o uso do cupom
                    cupom.uso_atual += 1
                    cupom.save()
            except Cupom.DoesNotExist:
                pass
    
    def get_total_final(self):
        """Retorna o total final com desconto aplicado"""
        if self.desconto:
            return float(self.total - self.desconto)  # Converte para float apenas no retorno
        return float(self.total)
    
    def get_total_final_decimal(self):
        """Retorna o total final como Decimal (melhor para cálculos)"""
        if self.desconto:
            return self.total - self.desconto
        return self.total


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    produto = models.CharField(max_length=255)
    produto_id = models.PositiveIntegerField()
    variacao = models.CharField(max_length=255)
    variacao_id = models.PositiveIntegerField()
    preco = models.FloatField()
    preco_promocional = models.FloatField(default=0)
    quantidade = models.PositiveIntegerField()
    imagem = models.CharField(max_length=2000)

    def __str__(self):
        return f'Item do {self.pedido}'
    
    class Meta:
        verbose_name = 'Item do pedido'
        verbose_name_plural = 'Itens do pedido'