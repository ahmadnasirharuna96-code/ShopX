from django.urls import path
from .views import USSDCallbackView

urlpatterns = [
    path("callback/", USSDCallbackView.as_view(), name="ussd-callback"),
]
