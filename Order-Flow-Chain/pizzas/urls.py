from django.urls import path
from .views import (
    PizzaBaseListView,
    CheeseTypeListView,
    ToppingsListView,
    PizzaListCreateView,
    OrderListCreateView,
)

urlpatterns = [
    path("pizza-bases/", PizzaBaseListView.as_view(), name="pizzabase-list"),
    path("cheese-types/", CheeseTypeListView.as_view(), name="cheesetype-list"),
    path("toppings/", ToppingsListView.as_view(), name="toppings-list"),
    path("pizzas/", PizzaListCreateView.as_view(), name="pizzas-list-create"),
    path("orders/", OrderListCreateView.as_view(), name="orders-list-create"),
]
