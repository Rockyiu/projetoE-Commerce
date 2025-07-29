from django.contrib import admin
from . import models


class itemPedidoInline(admin.TabularInline):
    model = models.ItemPedido
    extra = 1

class PedidoAdmin(admin.ModelAdmin):
    inline = [
        itemPedidoInline
    ]


admin.site.register(models.Pedido, PedidoAdmin)
admin.site.register(models.ItemPedido)

