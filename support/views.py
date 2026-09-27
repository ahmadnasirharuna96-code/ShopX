from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from businesses.models import Business
from customers.models import Customer
from orders.models import Order
from support.models import Conversation, Message, MessageType, SupportTicket, SupportTicketCategory


@login_required
def customer_support_chat_view(request, order_number):
    customer = getattr(request.user, "customer_profile", None)
    if not customer:
        return redirect("shop-home")

    order = get_object_or_404(Order.objects.select_related("customer", "business").prefetch_related("items"), order_number=order_number, customer=customer)
    business = order.business
    conversation, _ = Conversation.objects.get_or_create(customer=customer, business=business, order=order)

    if request.method == "POST":
        content = (request.POST.get("message") or "").strip()
        if content:
            Message.objects.create(
                conversation=conversation,
                sender="customer",
                message_type=MessageType.TEXT,
                content=content,
            )
            messages.success(request, "Your message has been sent.")
        return redirect("customer-order-support", order_number=order.order_number)

    context = {
        "order": order,
        "business": business,
        "conversation": conversation,
        "messages": conversation.messages.all(),
    }
    return render(request, "support/customer_chat.html", context)


@login_required
def support_ticket_create_view(request, order_number):
    customer = getattr(request.user, "customer_profile", None)
    if not customer:
        messages.error(request, "Please log in as a customer to report a problem.")
        return redirect("shop-home")

    order = get_object_or_404(Order.objects.select_related("customer", "business"), order_number=order_number, customer=customer)

    if request.method == "POST":
        category = request.POST.get("category") or SupportTicketCategory.OTHER
        subject = request.POST.get("subject") or f"Issue for Order #{order.order_number}"
        description = request.POST.get("description") or "Customer reported a problem."

        ticket = SupportTicket.objects.create(
            customer=customer,
            business=order.business,
            order=order,
            ticket_number=f"SUP-{order.order_number[-4:]}-{len(SupportTicket.objects.filter(customer=customer)) + 1}",
            category=category,
            subject=subject,
            description=description,
        )
        messages.success(request, f"Support ticket {ticket.ticket_number} created successfully.")
        return redirect("shop-my-orders")

    return render(request, "support/ticket_form.html", {"order": order})


@login_required
def business_support_index_view(request):
    business = getattr(request.user, "owned_business", None)
    if not business:
        messages.error(request, "Please set up your business profile first.")
        return redirect("dashboard-overview")

    conversations = Conversation.objects.filter(business=business).select_related("customer", "order").prefetch_related("messages")
    context = {"business": business, "conversations": conversations}
    return render(request, "support/business_support.html", context)


@login_required
def business_support_chat_view(request, pk):
    business = getattr(request.user, "owned_business", None)
    if not business:
        return redirect("dashboard-overview")

    conversation = get_object_or_404(Conversation.objects.select_related("customer", "business", "order"), pk=pk, business=business)

    if request.method == "POST":
        content = (request.POST.get("message") or "").strip()
        if content:
            Message.objects.create(
                conversation=conversation,
                sender="business",
                message_type=MessageType.TEXT,
                content=content,
            )
            messages.success(request, "Reply sent to the customer.")
        return redirect("dashboard-support-chat", pk=conversation.pk)

    context = {"conversation": conversation, "messages": conversation.messages.all()}
    return render(request, "support/business_chat.html", context)
