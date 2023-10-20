from django.contrib import admin
from .models import PizzaBase, CheeseType, Toppings, Pizza, Order

admin.site.register(PizzaBase)
admin.site.register(CheeseType)
admin.site.register(Toppings)
admin.site.register(Pizza)
admin.site.register(Order)
