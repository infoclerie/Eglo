from django.urls import path

from . import views

urlpatterns = [
    path("invoices/", views.invoices, name="invoices"),
    path("invoices/<int:pk>/", views.invoice_detail, name="invoice"),
    path("invoices/<int:pk>/xml/", views.invoice_xml, name="invoice_xml"),
    path("invoices/<int:pk>/onizleme/", views.invoice_preview, name="invoice_preview"),
    path("balances/", views.balances, name="balances"),
    path("statement/<int:partner_id>/", views.statement_view, name="statement"),
    path("cashflow/", views.cashflow, name="cashflow"),
    path("profitability/", views.profitability, name="profitability"),
]
