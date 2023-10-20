import logging
from django.db import models

logger = logging.getLogger(__name__)


class PizzaBase(models.Model):
    name = models.CharField(max_length=50)

    def save(self, *args, **kwargs):
        logger.info(f"Saving PizzaBase with name: {self.name}")
        super(PizzaBase, self).save(*args, **kwargs)


class CheeseType(models.Model):
    name = models.CharField(max_length=50)

    def save(self, *args, **kwargs):
        logger.info(f"Saving CheeseType with name: {self.name}")
        super(CheeseType, self).save(*args, **kwargs)


class Toppings(models.Model):
    name = models.CharField(max_length=50)

    def save(self, *args, **kwargs):
        logger.info(f"Saving Toppings with name: {self.name}")
        super(Toppings, self).save(*args, **kwargs)


class Pizza(models.Model):
    pizza_base = models.ForeignKey(PizzaBase, on_delete=models.CASCADE)
    cheese_type = models.ForeignKey(CheeseType, on_delete=models.CASCADE)
    toppings = models.ManyToManyField(Toppings)
    price = models.DecimalField(max_digits=5, decimal_places=2)

    def save(self, *args, **kwargs):
        logger.info(
            f"Saving Pizza with base: {self.pizza_base.name} and cheese type: {self.cheese_type.name}"
        )
        super(Pizza, self).save(*args, **kwargs)


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

    def save(self, *args, **kwargs):
        super(Order, self).save(*args, **kwargs)
