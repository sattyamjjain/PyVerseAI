from rest_framework import generics
from .models import PizzaBase, CheeseType, Toppings, Pizza, Order
from .serializers import (
    PizzaBaseSerializer,
    CheeseTypeSerializer,
    ToppingsSerializer,
    PizzaSerializer,
    OrderSerializer,
)


class PizzaBaseListView(generics.ListAPIView):
    queryset = PizzaBase.objects.all()
    serializer_class = PizzaBaseSerializer


class CheeseTypeListView(generics.ListAPIView):
    queryset = CheeseType.objects.all()
    serializer_class = CheeseTypeSerializer


class ToppingsListView(generics.ListAPIView):
    queryset = Toppings.objects.all()
    serializer_class = ToppingsSerializer


class PizzaListCreateView(generics.ListCreateAPIView):
    queryset = Pizza.objects.all()
    serializer_class = PizzaSerializer


class OrderListCreateView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
