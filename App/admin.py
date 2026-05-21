from django.contrib import admin
from .models import User, Product, Review, Order, OrderItem, Category

admin.site.register(User)
admin.site.register(Product)
admin.site.register(Review)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Category)