from django import forms
from .models import Business


class BusinessProfileForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = ["name", "description", "phone_number", "address", "city", "state", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "phone_number": forms.TextInput(attrs={"class": "form-input"}),
            "description": forms.Textarea(attrs={"class": "form-textarea", "rows": 3}),
            "address": forms.Textarea(attrs={"class": "form-textarea", "rows": 2}),
            "city": forms.TextInput(attrs={"class": "form-input"}),
            "state": forms.TextInput(attrs={"class": "form-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }
