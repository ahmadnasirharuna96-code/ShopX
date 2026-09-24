from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from .services import USSDService


@method_decorator(csrf_exempt, name="dispatch")
class USSDCallbackView(View):
    """
    Africa's Talking USSD Callback Endpoint.
    Handles HTTP POST requests from Africa's Talking USSD gateway.
    """

    def post(self, request, *args, **kwargs):
        # Africa's Talking sends form-urlencoded data
        session_id = request.POST.get("sessionId", "").strip()
        service_code = request.POST.get("serviceCode", "").strip()
        phone_number = request.POST.get("phoneNumber", "").strip()
        text = request.POST.get("text", "").strip()

        if not session_id or not phone_number:
            return HttpResponse("END Invalid request payload.", content_type="text/plain")

        response_text = USSDService.handle_request(
            session_id=session_id,
            phone_number=phone_number,
            text=text
        )

        return HttpResponse(response_text, content_type="text/plain")

    def get(self, request, *args, **kwargs):
        return HttpResponse("ShopX USSD Gateway Active. Send POST callback requests.", content_type="text/plain")
