import logging
from celery import shared_task
from django.utils.timezone import now
from datetime import timedelta
from .models import Order

# Create a logger instance for this module
logger = logging.getLogger(__name__)


@shared_task
def update_all_orders_status():
    logger.info("Initiating update of order statuses.")
    orders_to_update = Order.objects.exclude(status="DE").values_list("id", flat=True)

    for order_id in orders_to_update:
        order = Order.objects.get(id=order_id)

        if order.status == "PL" and now() > order.timestamp + timedelta(minutes=1):
            order.status = "AC"
            order.save()
            logger.info(f"Order {order_id} status updated to 'Accepted'.")

        elif order.status == "AC" and now() > order.timestamp + timedelta(minutes=2):
            order.status = "PR"
            order.save()
            logger.info(f"Order {order_id} status updated to 'Preparing'.")

        elif order.status == "PR" and now() > order.timestamp + timedelta(minutes=5):
            order.status = "DI"
            order.save()
            logger.info(f"Order {order_id} status updated to 'Dispatched'.")

        elif order.status == "DI" and now() > order.timestamp + timedelta(minutes=10):
            order.status = "DE"
            order.save()
            logger.info(f"Order {order_id} status updated to 'Delivered'.")

    logger.info("Order status update task completed.")
