from django.db import models
from common.models import TimeStampedModel


class USSDSession(TimeStampedModel):
    session_id = models.CharField(max_length=255, unique=True, db_index=True)
    phone_number = models.CharField(max_length=30, db_index=True)
    current_state = models.CharField(max_length=50, default="START", db_index=True)
    business_id = models.IntegerField(null=True, blank=True)
    category_id = models.IntegerField(null=True, blank=True)
    product_id = models.IntegerField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    temp_data = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"USSD Session {self.session_id} ({self.phone_number}) - State: {self.current_state}"
