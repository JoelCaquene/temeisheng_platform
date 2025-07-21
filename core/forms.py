# core/forms.py (ATUALIZADO E COMPLETO)

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm
from .models import User, Deposito, Saque, CoordenadaBancaria, Nivel # Importar Nivel também

class UserRegistrationForm(forms.ModelForm):
    phone_number = forms.CharField(label="Número de Telefone", max_length=15, 
                                   widget=forms.TextInput(attrs={'placeholder': 'Ex: 9XXXXXXXX'}))
    password = forms.CharField(label="Senha", widget=forms.PasswordInput(attrs={'placeholder': 'Mínimo 4 dígitos'}))
    password_confirm = forms.CharField(label="Confirmar Senha", widget=forms.PasswordInput(attrs={'placeholder': 'Confirme sua senha'}))
    
    # ATUALIZADO: Usar 'referral_code' em vez de 'inviter_phone'
    # Este campo não será salvo diretamente no modelo User, mas será usado para lógica na view.
    referral_code_inviter = forms.CharField(label="Código de Convite (Opcional)", max_length=10, required=False,
                                            widget=forms.TextInput(attrs={'placeholder': 'Se alguém te convidou'}))

    class Meta:
        model = User
        # ATUALIZADO: 'referral_code_inviter' não faz parte do modelo User, então não pode estar em 'fields'
        # Removemos 'inviter_phone' e não adicionamos 'referral_code_inviter' aqui
        fields = ['phone_number', 'password', 'password_confirm'] 

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "As senhas não coincidem.")
        
        if password and len(password) < 4: 
            self.add_error('password', "A senha deve ter no mínimo 4 dígitos.")
            
        # O 'referral_code_inviter' será validado na view se um usuário com esse código existe
        # Não precisamos de validação específica aqui no formulário para ele.

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(label="Número de Telefone", 
                               widget=forms.TextInput(attrs={'placeholder': 'Seu número de telefone'}))
    password = forms.CharField(label="Senha", 
                               widget=forms.PasswordInput(attrs={'placeholder': 'Sua senha'}))

class DepositoForm(forms.ModelForm):
    # Campos para seleção de banco e nível
    coordenada_bancaria_usada = forms.ModelChoiceField(
        queryset=CoordenadaBancaria.objects.filter(is_active=True),
        label="Selecione o Banco para Depósito",
        empty_label="-- Selecione um banco --",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    nivel_ativar = forms.ModelChoiceField(
        queryset=Nivel.objects.filter(is_active=True).order_by('deposito_minimo'),
        label="Selecione o Nível a Ativar",
        empty_label="-- Selecione um nível --",
        required=False, # Nível pode ser selecionado, mas não é obrigatório no form de depósito
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Deposito
        # CORREÇÃO APLICADA AQUI: O campo 'comprovante_pix' foi incluído novamente
        fields = ['valor', 'comprovante_pix', 'coordenada_bancaria_usada', 'nivel_ativar'] 
        widgets = {
            'valor': forms.NumberInput(attrs={'placeholder': 'Ex: 1500.00', 'class': 'form-control'}),
            # CORREÇÃO APLICADA AQUI: 'comprovante_pix' agora usa FileInput
            'comprovante_pix': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'valor': 'Digite o Valor do Depósito (KZ):',
            # CORREÇÃO APLICADA AQUI: Label para 'comprovante_pix'
            'comprovante_pix': 'Carregar Comprovativo:',
        }

    def clean_valor(self):
        valor = self.cleaned_data['valor']
        if valor <= 0:
            raise forms.ValidationError("O valor do depósito deve ser maior que zero.")
        return valor

class SaqueForm(forms.ModelForm):
    class Meta:
        model = Saque
        fields = ['valor'] 
        widgets = {
            'valor': forms.NumberInput(attrs={'placeholder': 'Ex: 5000.00', 'class': 'form-control'}),
        }
        labels = {
            'valor': 'Valor do Saque (KZ):',
        }

    def clean_valor(self):
        valor = self.cleaned_data['valor']
        if valor <= 0:
            raise forms.ValidationError("O valor do saque deve ser maior que zero.")
        return valor

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(label="Senha Antiga", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password1 = forms.CharField(label="Nova Senha", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password2 = forms.CharField(label="Confirme a Nova Senha", widget=forms.PasswordInput(attrs={'class': 'form-control'}))

class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(label="Nova Senha", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password2 = forms.CharField(label="Confirme a Nova Senha", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    