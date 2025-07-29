from django.db import models
from perfil.models import Perfil
from django.forms import ValidationError
import re

class Endereco(models.Model):
    perfil = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name='enderecos', null=True, blank=True)
    apelido = models.CharField(max_length=50, blank=True, help_text="Ex: Casa, Trabalho, Mãe")
    cep = models.CharField(max_length=9)
    rua = models.CharField(max_length=255)
    numero = models.CharField(max_length=10)
    complemento = models.CharField(max_length=255, blank=True, null=True)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(
        max_length=2,
        default='SP',
        choices=(
            ('AC', 'Acre'),
            ('AL', 'Alagoas'),
            ('AP', 'Amapá'),
            ('AM', 'Amazonas'),
            ('BA', 'Bahia'),
            ('CE', 'Ceará'),
            ('DF', 'Distrito Federal'),
            ('ES', 'Espírito Santo'),
            ('GO', 'Goiás'),
            ('MA', 'Maranhão'),
            ('MT', 'Mato Grosso'),
            ('MS', 'Mato Grosso do Sul'),
            ('MG', 'Minas Gerais'),
            ('PA', 'Pará'),
            ('PB', 'Paraíba'),
            ('PR', 'Paraná'),
            ('PE', 'Pernambuco'),
            ('PI', 'Piauí'),
            ('RJ', 'Rio de Janeiro'),
            ('RN', 'Rio Grande do Norte'),
            ('RS', 'Rio Grande do Sul'),
            ('RO', 'Rondônia'),
            ('RR', 'Roraima'),
            ('SC', 'Santa Catarina'),
            ('SP', 'São Paulo'),
            ('SE', 'Sergipe'),
            ('TO', 'Tocantins'),
        )     
    )  # Ex: SP, RJ
    pais = models.CharField(max_length=50, default='Brasil')
    principal = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.apelido or 'Endereço'} - {self.cidade}/{self.estado}"
    
    def clean(self):
        error_messages = {}
        if re.search(r'[^0-9]', self.cep) or len(self.cep) < 8:
            error_messages['cep'] = 'CEP inválido, digite os 8 digitos do CEP'
          # Rua obrigatória
        if not str(self.rua or '').strip():
            error_messages['rua'] = 'O campo rua é obrigatório.'

        # Número: letras e números permitidos, mas não pode estar vazio
        if not str(self.numero or '').strip():
            error_messages['numero'] = 'O número é obrigatório.'

        # Bairro obrigatório
        if not str(self.bairro or '').strip():
            error_messages['bairro'] = 'O bairro é obrigatório.'

        # Cidade obrigatória
        if not str(self.cidade or '').strip():
            error_messages['cidade'] = 'A cidade é obrigatória.'

        if error_messages:
            raise ValidationError(error_messages)
    
    class Meta:
        verbose_name = 'Endereço'
        verbose_name_plural = 'Endereços'
