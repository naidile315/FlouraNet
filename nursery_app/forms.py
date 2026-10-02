from django import forms
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from .models import ContactMessage


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}))
   # phone = forms.CharField(
    #    required=True,
     #   validators=[RegexValidator(r'^\d{10}$', message='Enter a valid 10-digit phone number')],
      #  widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone (10 digits)'}),
    #)
    phone = forms.CharField(
        required=True,
        validators=[
            RegexValidator(
                regex=r'^[6-9]\d{9}$',
                message='Enter a valid Phone number'
            )
        ],
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Phone '}
        )
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}),
        }

    def clean(self):
        cleaned = super().clean()
        p = cleaned.get('password')
        cp = cleaned.get('confirm_password')
        if p and cp and p != cp:
            raise forms.ValidationError('Passwords do not match')
        return cleaned


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'How can we help you?'}),
        }


class NotifyRequestForm(forms.Form):
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your email (optional)'}))


class CheckoutForm(forms.Form):
    STATE_CHOICES = [
        ('', 'Choose state'),
        ('Karnataka', 'Karnataka'),
        ('Maharashtra', 'Maharashtra'),
        ('Tamil Nadu', 'Tamil Nadu'),
        ('Kerala', 'Kerala'),
        ('Delhi', 'Delhi'),
    ]

    DISTRICT_MAP = {
        'Karnataka': [('', 'Choose city'), ('Bengaluru', 'Bengaluru'), ('Mysuru', 'Mysuru'), ('Mangalore', 'Mangalore'), ('Hubli', 'Hubli')],
        'Maharashtra': [('', 'Choose city'), ('Mumbai', 'Mumbai'), ('Pune', 'Pune'), ('Nagpur', 'Nagpur'), ('Nashik', 'Nashik')],
        'Tamil Nadu': [('', 'Choose city'), ('Chennai', 'Chennai'), ('Coimbatore', 'Coimbatore'), ('Madurai', 'Madurai'), ('Tiruchirappalli', 'Tiruchirappalli')],
        'Kerala': [('', 'Choose city'), ('Thiruvananthapuram', 'Thiruvananthapuram'), ('Kochi', 'Kochi'), ('Kozhikode', 'Kozhikode'), ('Thrissur', 'Thrissur')],
        'Delhi': [('', 'Choose city'), ('New Delhi', 'New Delhi'), ('Central Delhi', 'Central Delhi'), ('South Delhi', 'South Delhi')],
    }

    state = forms.ChoiceField(choices=STATE_CHOICES, required=True,
                              widget=forms.Select(attrs={'class': 'form-control'}))
    # Keep model column name as 'district' for compatibility, but show label as 'City'
    district = forms.ChoiceField(label='City', choices=[('', 'Choose city')], required=True,
                                 widget=forms.Select(attrs={'class': 'form-control'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=True)
    payment_method = forms.ChoiceField(choices=[('razorpay', 'QR')], widget=forms.Select(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data = self.data if self.is_bound else self.initial
        state = data.get('state', '')
        if state in self.DISTRICT_MAP:
            self.fields['district'].choices = self.DISTRICT_MAP[state]
        else:
            self.fields['district'].choices = [('', 'Choose city')]
