from django.contrib import admin
from .models import PizzaBase, CheeseType, Toppings

admin.site.register(PizzaBase)
admin.site.register(CheeseType)
admin.site.register(Toppings)
