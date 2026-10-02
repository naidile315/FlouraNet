from django.contrib import admin
from .models import Category, Plant, CartItem, Order, ContactMessage
from .models import Profile
# from .models import OrderItem

# @admin.register(OrderItem)
# class OrderItemAdmin(admin.ModelAdmin):
#     list_display = ('order', 'plant', 'quantity', 'price')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock', 'image_tag')
    list_filter = ('category',)
    readonly_fields = ('image_tag',)

    def image_tag(self, obj):
        if obj.image:
            return f'<a href="{obj.get_absolute_url()}" target="_blank"><img src="{obj.image.url}" style="height:48px;width:auto;"/></a>'
        return ''
    image_tag.allow_tags = True
    image_tag.short_description = 'Image'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'plant', 'quantity')


# @admin.register(Order)
# class OrderAdmin(admin.ModelAdmin):
#     list_display = ('id', 'user', 'total_amount', 'status', 'order_date')
#     list_filter = ('status',)
#     readonly_fields = ('items_json',)
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_amount', 'status', 'order_date')
    list_filter = ('status', 'user')  # 👈 add user here
    readonly_fields = ('items_json',)
    search_fields = ('user__username', 'status')  # 👈 optional: allows searching by username
    # fields = ('user', 'items_json', 'total_amount', 'status', 'order_date', 'expected_delivery_date', 'payment_id')




@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone')


from .models import NotifyRequest


@admin.register(NotifyRequest)
class NotifyRequestAdmin(admin.ModelAdmin):
    list_display = ('plant', 'email', 'user', 'created_at', 'notified')
    list_filter = ('notified', 'created_at')
    actions = ['mark_notified']

    def mark_notified(self, request, queryset):
        queryset.update(notified=True)
    mark_notified.short_description = 'Mark selected as notified'


# Add an admin URL for the analytics dashboard so it lives under the admin/ namespace
from django.urls import path
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from . import views as _views

def _get_admin_urls(original_get_urls):
    def get_urls():
        urls = original_get_urls()
        my_urls = [
            path('dashboard/', staff_member_required(_views.admin_dashboard), name='admin-dashboard'),
        ]
        # put our URL before the default admin URLs so it appears at /admin/dashboard/
        return my_urls + urls
    return get_urls

# patch the admin site's get_urls to include our dashboard
admin.site.get_urls = _get_admin_urls(admin.site.get_urls)


# -----------------------------------------------------------------------------
# Add a small admin URL so the Django admin can link to the site analytics
# We attach a simple view under the admin URL namespace: /admin/dashboard/
# This keeps the dashboard protected by the admin site's permission checks.
# -----------------------------------------------------------------------------
from django.urls import path


def _dashboard_view(request):
    # Import here to avoid circular imports at module load
    from . import views as app_views
    # reuse the existing admin_dashboard view (it returns a rendered TemplateResponse)
    return app_views.admin_dashboard(request)


# Extend admin site's URL patterns to include our dashboard view.
# We patch admin.site.get_urls to prefix our URL so reverse('admin:admin-dashboard') works.
_original_get_urls = admin.site.get_urls


def _get_urls():
    my_urls = [
        path('dashboard/', admin.site.admin_view(_dashboard_view), name='admin-dashboard'),
    ]
    return my_urls + _original_get_urls()


admin.site.get_urls = _get_urls
