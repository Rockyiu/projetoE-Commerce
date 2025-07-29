# pedido/urls.py
from django.urls import path
from . import views

app_name = 'pedido'

urlpatterns = [
    # URLs básicas
    path('pagar/<int:pk>/', views.Pagar.as_view(), name="pagar"),
    path('salvarpedido/', views.SalvarPedido.as_view(), name="salvarpedido"),
    path('lista/', views.Lista.as_view(), name="lista"),
    path('detalhe/<int:pk>/', views.Detalhe.as_view(), name="detalhe"),
    
    # Pagamento com Cartão (Stripe)
    path('processar-pagamento/<int:pk>/', views.ProcessarPagamento.as_view(), name='processar_pagamento'),
    path('criar-intento-pagamento/<int:pk>/', views.CriarIntentoPagamento.as_view(), name='criar_intento_pagamento'),
    
    # PIX
    path('processar-pagamento-pix/<int:pk>/', views.ProcessarPagamentoPix.as_view(), name='processar_pagamento_pix'),
    path('pix-qrcode/<int:pk>/', views.PixQRCode.as_view(), name='pix_qrcode'),
    path('pix-confirmacao/<int:pk>/', views.PixQRCode.as_view(), name='pix_confirmacao'),
    
    # Boleto
    path('processar-pagamento-boleto/<int:pk>/', views.ProcessarPagamentoBoleto.as_view(), name='processar_pagamento_boleto'),
    path('boleto_vizualizar/<int:pk>/', views.BoletoVizualizar.as_view(), name='boleto_vizualizar'),
    path('boleto-confirmacao/<int:pk>/', views.BoletoVizualizar.as_view(), name='boleto_confirmacao'),
    
    # API para verificar status
    path('verificar-status-pagamento/', views.VerificarStatusPagamento.as_view(), name='verificar_status_pagamento'),
    
    # Webhook Stripe
    path('webhook/stripe/', views.WebhookStripe.as_view(), name='webhook_stripe'),
    
    # Rota de teste (remover em produção)
    path('teste-stripe/', views.teste_stripe, name='teste_stripe'),
]