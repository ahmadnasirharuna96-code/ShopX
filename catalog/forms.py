from django import forms
from .models import Product, Category


class ProductForm(forms.ModelForm):
    initial_stock = forms.IntegerField(
        min_value=0,
        initial=10,
        required=False,
        label="Initial Stock Quantity",
        help_text="Set starting inventory stock."
    )
    low_stock_threshold = forms.IntegerField(
        min_value=1,
        initial=5,
        required=False,
        label="Low Stock Warning Threshold"
    )

    class Meta:
        model = Product
        fields = ["name", "category", "price", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "price": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
            "description": forms.Textarea(attrs={"class": "form-textarea", "rows": 3}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }
