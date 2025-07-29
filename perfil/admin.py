from django.contrib import admin
from . import models
from enderecos.models import Endereco



class EnderecoInline(admin.TabularInline):
    model = Endereco
    extra = 1  


class PerfilAdmin(admin.ModelAdmin):
    inlines = [
        EnderecoInline
        ]  

admin.site.register(models.Perfil, PerfilAdmin)

