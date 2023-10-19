from celery import shared_task
from django.utils.timezone import now
from datetime import timedelta
from .models import Order


@shared_task
def update_order_status(order_id):
    order = Order.objects.get(id=order_id)

    if order.status == "PL" and now() > order.timestamp + timedelta(minutes=1):
        order.status = "AC"
        order.save()

    elif order.status == "AC" and now() > order.timestamp + timedelta(minutes=2):
        order.status = "PR"
        order.save()

    elif order.status == "PR" and now() > order.timestamp + timedelta(minutes=5):
        order.status = "DI"
        order.save()

    elif order.status == "DI" and now() > order.timestamp + timedelta(minutes=10):
        order.status = "DE"
        order.save()
