from django.urls import path
from . import views

app_name = 'nursery_app'

urlpatterns = [
    # Make login the first page: map root ('') to the login view.
    path('', views.register_view, name='index'),
    # Keep the home view available under /home/ and preserve the 'home' URL name
    path('home/', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('plant/<int:pk>/', views.plant_detail, name='plant_detail'),
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:pk>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update-quantity/', views.update_cart_quantity, name='update_cart_quantity'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_history, name='order_history'),
    path('contact/', views.contact_view, name='contact'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('notify/', views.notify_request, name='notify_request'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),
    path('payment/verify/', views.payment_verify, name='payment_verify'),
    path('payment/webhook/', views.payment_webhook, name='payment_webhook'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/export-csv/', views.export_plant_sales_csv, name='export_plant_sales_csv'),
    path('admin-dashboard/export-revenue-csv/', views.export_yearly_revenue_csv, name='export_yearly_revenue_csv'),
    path('admin-dashboard/export-matrix-csv/', views.export_matrix_csv, name='export_matrix_csv'),
    path('admin-dashboard/export-orders-csv/', views.export_orders_csv, name='export_orders_csv'),
    path('chart-data/revenue/', views.revenue_chart_data, name='revenue_chart_data'),
]
