from django import forms
from .models import Inventory


class StockAdjustmentForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=0,
        required=True,
        label="Total Physical Stock Quantity"
    )
    low_stock_threshold = forms.IntegerField(
        min_value=1,
        required=True,
        label="Low Stock Alert Threshold"
    )
