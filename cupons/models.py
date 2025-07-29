# cupons/models.py - Crie um novo app chamado 'cupons'

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class Cupom(models.Model):
    codigo = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Código do cupom que o usuário vai digitar"
    )
    desconto_percentual = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True,
        help_text="Desconto em porcentagem (0-100)"
    )
    desconto_valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Desconto em valor fixo (R$)"
    )
    valido_de = models.DateTimeField(default=timezone.now)
    valido_ate = models.DateTimeField()
    ativo = models.BooleanField(default=True)
    uso_maximo = models.IntegerField(
        default=100,
        help_text="Número máximo de vezes que o cupom pode ser usado"
    )
    uso_atual = models.IntegerField(default=0)
    valor_minimo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Valor mínimo do pedido para aplicar o cupom"
    )
    
    def __str__(self):
        return self.codigo
    
    def is_valido(self):
        now = timezone.now()
        return (
            self.ativo and 
            self.valido_de <= now <= self.valido_ate and
            self.uso_atual < self.uso_maximo
        )
    
    def calcular_desconto(self, total):
        """Calcula o valor do desconto baseado no total do carrinho"""
        if not self.is_valido():
            return 0
            
        if total < self.valor_minimo:
            return 0
            
        if self.desconto_percentual:
            return (total * self.desconto_percentual) / 100
        elif self.desconto_valor:
            return min(self.desconto_valor, total)  # Desconto não pode ser maior que o total
        return 0
    
    class Meta:
        verbose_name = 'Cupom'
        verbose_name_plural = 'Cupons'
        ordering = ['-id']