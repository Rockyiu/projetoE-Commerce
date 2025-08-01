# Generated by Django 5.2.4 on 2025-07-18 18:00

import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cupons', '0001_initial'),
        ('pedido', '0003_pedido_qtd_total'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='criado',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='pedido',
            name='cupom',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pedidos', to='cupons.cupom'),
        ),
        migrations.AddField(
            model_name='pedido',
            name='desconto',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Valor do desconto aplicado', max_digits=10),
        ),
        migrations.AlterField(
            model_name='pedido',
            name='status',
            field=models.CharField(choices=[('A', 'Aprovado'), ('CR', 'Criado'), ('R', 'Reprovado'), ('P', 'Pagamento pendente'), ('F', 'Falha no Pagamento'), ('P', 'Processando'), ('R', 'Reembolsado'), ('CO', 'Concluido'), ('C', 'Cancelado'), ('E', 'Enviado'), ('F', 'Finalizado')], default='CR', max_length=2),
        ),
    ]
