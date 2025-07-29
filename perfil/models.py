from django.db import models
from django.contrib.auth.models import User
from django.forms import ValidationError
import re
from utils.validacpf import valida_cpf
from datetime import date

class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    idade = models.PositiveBigIntegerField()
    data_nascimento = models.DateField()
    cpf = models.CharField(max_length=11)

    def __str__(self):
        return f'{self.usuario.first_name} {self.usuario.last_name}'
    
    def clean(self):
        error_messages = {}
        cpf_enviado = self.cpf or None
        cpf_salvo = None
        perfil = Perfil.objects.filter(cpf=cpf_enviado).first()

        if perfil:
            cpf_salvo = perfil.cpf
            if cpf_salvo is not None and self.pk != perfil.pk:
                error_messages['cpf'] = 'CPF já existe.'
                
        if not valida_cpf(self.cpf):
            error_messages['cpf'] = 'Digite um CPF inválido'

         # 2. Idade mínima de 18 anos
        if self.idade < 18:
            error_messages['idade'] = 'A idade mínima permitida é 18 anos.'

        # 3. Data de nascimento não pode ser no futuro
        hoje = date.today()
        if self.data_nascimento > hoje:
            error_messages['data_nascimento'] = 'A data de nascimento não pode estar no futuro.'

        # 4. Validação opcional: idade confere com a data de nascimento
        idade_calculada = hoje.year - self.data_nascimento.year - (
            (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day)
        )

        if self.idade != idade_calculada:
            error_messages['idade'] = (
                f'A idade informada não confere com a data de nascimento. '
                f'Idade correta: {idade_calculada} anos.'
            )

        
        if error_messages:
            raise ValidationError(error_messages)
      


    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfis'

