import os
from django import forms
from django.core.exceptions import ValidationError
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
    image = forms.ImageField(
        required=False,  # Checked dynamically in clean_image for mandatory new uploads
        label="Product Image * REQUIRED",
        help_text="Upload a clear product image (JPG, PNG, WEBP, GIF up to 5MB)."
    )

    class Meta:
        model = Product
        fields = ["name", "category", "price", "description", "image", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "required": "required"}),
            "category": forms.Select(attrs={"class": "form-select", "required": "required"}),
            "price": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "required": "required"}),
            "description": forms.Textarea(attrs={"class": "form-textarea", "rows": 3}),
            "image": forms.FileInput(attrs={"class": "form-file", "accept": "image/*", "onchange": "previewImage(this)"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        
        # Enforce mandatory image requirement for NEW products or products without existing image
        is_new_product = not self.instance or not self.instance.pk
        has_existing_image = self.instance and bool(self.instance.image)

        if is_new_product and not image:
            raise ValidationError("Product image is required.")

        if not image and not has_existing_image:
            raise ValidationError("Product image is required.")

        if image:
            # File extension validation
            ext = os.path.splitext(image.name)[1].lower()
            allowed = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
            if ext not in allowed:
                raise ValidationError(f"Unsupported file format '{ext}'. Allowed formats: JPG, PNG, WEBP, GIF.")

            # Max file size 5MB
            max_size = 5 * 1024 * 1024
            if image.size > max_size:
                raise ValidationError("Image file size must not exceed 5MB.")

        return image
