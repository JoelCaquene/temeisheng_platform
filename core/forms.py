# core/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm
from .models import User, Deposito, Saque, CoordenadaBancaria, Nivel # Importar Nivel também

class UserRegistrationForm(forms.ModelForm):
    phone_number = forms.CharField(label="Número de Telefone", max_length=15, 
                                   widget=forms.TextInput(attrs={'placeholder': 'Ex: 9XXXXXXXX'}))
    password = forms.CharField(label="Senha", widget=forms.PasswordInput(attrs={'placeholder': 'Mínimo 4 dígitos'}))
    password_confirm = forms.CharField(label="Confirmar Senha", widget=forms.PasswordInput(attrs={'placeholder': 'Confirme sua senha'}))
    inviter_phone = forms.CharField(label="Número do Convidante (Opcional)", max_length=15, required=False,
                                    widget=forms.TextInput(attrs={'placeholder': 'Se alguém te convidou'}))

    class Meta:
        model = User
        fields = ['phone_number', 'password', 'password_confirm', 'inviter_phone']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "As senhas não coincidem.")
        
        if password and len(password) < 4: # Django já valida o min_length pelo settings, mas é bom ter aqui
            self.add_error('password', "A senha deve ter no mínimo 4 dígitos.")
            
        # Não precisa validar inviter_phone aqui, será validado na view ou signal

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
        fields = ['valor', 'comprovativo', 'coordenada_bancaria_usada', 'nivel_ativar'] # Adicionado nivel_ativar
        widgets = {
            'valor': forms.NumberInput(attrs={'placeholder': 'Ex: 1500.00', 'class': 'form-control'}),
            'comprovativo': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'valor': 'Digite o Valor do Depósito (KZ):',
            'comprovativo': 'Carregar Comprovativo:',
        }

    def clean_valor(self):
        valor = self.cleaned_data['valor']
        if valor <= 0:
            raise forms.ValidationError("O valor do depósito deve ser maior que zero.")
        return valor

class SaqueForm(forms.ModelForm):
    # Campos de banco e IBAN REMOVIDOS do formulário.
    # Estes dados virão do perfil do usuário na view.
    class Meta:
        model = Saque
        fields = ['valor'] # Apenas o valor é pedido no formulário
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
    