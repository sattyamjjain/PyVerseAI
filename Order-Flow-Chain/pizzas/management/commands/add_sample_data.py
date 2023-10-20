from django.core.management.base import BaseCommand
from pizzas.models import PizzaBase, CheeseType, Toppings


class Command(BaseCommand):
    help = 'Add sample data to PizzaBase, CheeseType, and Toppings'

    def handle(self, *args, **kwargs):
        pizzabases = ["Thin Crust", "Thick Crust", "Cheese Burst"]
        cheesetypes = ["Mozzarella", "Cheddar", "Parmesan", "Provolone"]
        toppings = ["Olives", "Mushrooms", "Pepperoni", "Onions", "Bell Peppers", "Jalapenos", "Pineapple"]

        for base in pizzabases:
            PizzaBase.objects.get_or_create(name=base)

        for cheese in cheesetypes:
            CheeseType.objects.get_or_create(name=cheese)

        for topping in toppings:
            Toppings.objects.get_or_create(name=topping)

        self.stdout.write(self.style.SUCCESS(f"Successfully added sample data to the database!"))

