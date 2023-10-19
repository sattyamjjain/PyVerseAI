from rest_framework import serializers
from .models import PizzaBase, CheeseType, Toppings, Pizza, Order


class PizzaBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PizzaBase
        fields = "__all__"


class CheeseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheeseType
        fields = "__all__"


class ToppingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Toppings
        fields = "__all__"


class PizzaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pizza
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = "__all__"
