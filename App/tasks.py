from celery import shared_task

from django.core.mail import send_mail
from django.db.models import Sum
from django.utils.timezone import now

from Project import settings

from .models import (
    Product,
    Order,
    DailyStatistics
)


@shared_task
def send_order_email(user_email, order_id):
    send_mail(
        subject="Order Created",
        message=f"Order #{order_id} created successfully",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=False
    )

@shared_task
def update_product_stock(product_id):

    try:
        product = Product.objects.get(id=product_id)

        if product.stock == 0:
            print(f"{product.name} is Out of Stock")

        product.save()

    except Product.DoesNotExist:
        pass

@shared_task
def daily_statistics():

    today = now().date()

    orders = Order.objects.filter(
        created_at__date=today
    )

    total_orders = orders.count()

    total_income = (
        orders.aggregate(
            total=Sum("total_price")
        )["total"] or 0
    )

    DailyStatistics.objects.update_or_create(
        date=today,
        defaults={
            "total_orders": total_orders,
            "total_income": total_income
        }
    )