from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class BusinessRegistrationForm(UserCreationForm):
    business_name = forms.CharField(max_length=255, required=True, label="Business Name")
    business_phone = forms.CharField(max_length=20, required=True, label="Business Phone")
    business_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=True, label="Business Address")
    city = forms.CharField(max_length=100, required=True, label="City")
    state = forms.CharField(max_length=100, required=True, label="State")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "phone_number")
