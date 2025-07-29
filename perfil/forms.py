import email
from io import UnsupportedOperation
from django import forms
from django.contrib.auth.models import User
from . import models
from enderecos.models import Endereco


class PerfilForm(forms.ModelForm):
    class Meta:
        model = models.Perfil
        fields = '__all__'
        exclude = ('usuario',)

class UserForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(),
        label='Senha'
    )
    password2 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(),
        label='Confirmação senha'
    )

    def __init__(self, usuario=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.usuario = usuario 

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'password', 'password2', 'email')

    def clean(self, *args, **kwargs):
        data = self.data
        cleaned = self.cleaned_data
        validation_error_msgs = {}
        usuario_data = cleaned.get('username')
        password_data = cleaned.get('password')
        password2_data = cleaned.get('password2')
        email_data = cleaned.get('email')

        usuario_db = User.objects.filter(username=usuario_data).first()
        email_db = User.objects.filter(email=email_data).first()

        error_msg_user_exists = 'Usuario já existe'
        error_msg_email_exists = 'E-mail já existe'
        error_msg_password_match = 'As duas senhas não conferem'
        error_msg_password_short = 'Sua senha precisa de pelo menos 8 caracteres'
        error_msg_password_number = 'Sua senhha precisa de pelo menos um numero'
        error_msg_password_caracter = 'Sua senha precisa de pelo menos um caracter'
        error_msg_required_field = 'Este campo é obrigatório'

        if self.usuario:
            if usuario_db:
                if usuario_data != usuario_db.username:
                    validation_error_msgs['username'] = error_msg_user_exists
                
            if email_db:
                if email_data != email_db.email: 
                    validation_error_msgs['email'] = error_msg_email_exists

            if password_data:
                if password_data != password2_data:
                    validation_error_msgs['password'] = error_msg_password_match
                    validation_error_msgs['password2'] = error_msg_password_match
                
                if len(password_data) < 8:
                    validation_error_msgs['password'] = error_msg_password_short
                elif not any(char.isdigit() for char in password_data):
                    validation_error_msgs['password'] = error_msg_password_number
                elif not any(not char.isalnum() for char in password_data):
                    validation_error_msgs['password'] = error_msg_password_caracter
                

        else:
            if usuario_db:
                validation_error_msgs['username'] = error_msg_user_exists
                
            if email_db: 
                validation_error_msgs['email'] = error_msg_email_exists

            if not password_data:
                validation_error_msgs['password'] = error_msg_required_field
            
            if not password2_data:
                validation_error_msgs['password'] = error_msg_required_field

            if password_data and password2_data:
                if password_data != password2_data:
                    validation_error_msgs['password'] = error_msg_password_match
                    validation_error_msgs['password2'] = error_msg_password_match

                if len(password_data) < 8:
                    validation_error_msgs['password'] = error_msg_password_short
                elif not any(char.isdigit() for char in password_data):
                    validation_error_msgs['password'] = error_msg_password_number
                elif not any(not char.isalnum() for char in password_data):
                    validation_error_msgs['password'] = error_msg_password_caracter


        if validation_error_msgs:
            raise(forms.ValidationError(validation_error_msgs))
        
    
class EnderecoForm(forms.ModelForm):
    class Meta:
        model = Endereco
        fields = '__all__'
        exclude = ('perfil',)
        labels = {
            'apelido': 'Apelido do endereço',
            'cep': 'CEP',
            'rua': 'Rua',
            'numero': 'Número',
            'complemento': 'Complemento',
            'bairro': 'Bairro',
            'cidade': 'Cidade',
            'estado': 'Estado',
            'pais': 'País',
            'principal': 'Endereço principal'
        }