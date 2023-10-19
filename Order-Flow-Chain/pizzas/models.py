from django.db import models


class PizzaBase(models.Model):
    name = models.CharField(max_length=50)


class CheeseType(models.Model):
    name = models.CharField(max_length=50)


class Toppings(models.Model):
    name = models.CharField(max_length=50)


class Pizza(models.Model):
    pizza_base = models.ForeignKey(PizzaBase, on_delete=models.CASCADE)
    cheese_type = models.ForeignKey(CheeseType, on_delete=models.CASCADE)
    toppings = models.ManyToManyField(Toppings)
    price = models.DecimalField(max_digits=5, decimal_places=2)


class Order(models.Model):
    STATUSES = [
        ("PL", "Placed"),
        ("AC", "Accepted"),
        ("PR", "Preparing"),
        ("DI", "Dispatched"),
        ("DE", "Delivered"),
    ]
    status = models.CharField(max_length=2, choices=STATUSES, default="PL")
    timestamp = models.DateTimeField(auto_now_add=True)
    pizzas = models.ManyToManyField(Pizza)
