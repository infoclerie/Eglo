from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("sepet/", views.cart, name="cart"),
    path("siparisler/", views.orders, name="orders"),
    path("siparisler/<int:pk>/", views.order_detail, name="order"),
    path("faturalar/", views.invoices, name="invoices"),
    path("faturalar/<int:pk>/xml/", views.invoice_xml, name="invoice_xml"),
    path("ekstre/", views.statement, name="statement"),
]
