# utils/password_validators.py

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class CustomPasswordValidator:
    """
    Validador que implementa as mesmas regras do seu formulário:
    - Mínimo 8 caracteres
    - Pelo menos um número
    - Pelo menos um caractere especial
    """
    
    def validate(self, password, user=None):
        # Verifica tamanho mínimo
        if len(password) < 8:
            raise ValidationError(
                _("Sua senha precisa de pelo menos 8 caracteres"),
                code='password_too_short',
            )
        
        # Verifica se tem pelo menos um número
        if not any(char.isdigit() for char in password):
            raise ValidationError(
                _("Sua senha precisa de pelo menos um numero"),
                code='password_no_digit',
            )
        
        # Verifica se tem pelo menos um caractere especial (não alfanumérico)
        if not any(not char.isalnum() for char in password):
            raise ValidationError(
                _("Sua senha precisa de pelo menos um caracter especial"),
                code='password_no_special',
            )
    
    def get_help_text(self):
        return _(
            "Sua senha deve conter pelo menos 8 caracteres, "
            "incluindo pelo menos um número e um caractere especial."
        )