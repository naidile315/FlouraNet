from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Plant(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='plants')
    price = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField(blank=True)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='plants/', blank=True, null=True)
    wiki_link = models.URLField(blank=True, null=True, help_text="Optional: link to more info about the plant")
    # order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='order_items')
    # order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='order_items', null=True, blank=True)
    # plants = models.ForeignKey('Plant', on_delete=models.CASCADE , null=True, blank=True)
    # quantity = models.PositiveIntegerField(null=True, blank=True)
    
    # def __str__(self):
    #     return f"{self.quantity} * {self.plant.name}"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('nursery_app:plant_detail', args=[str(self.pk)])


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def total_price(self):
        return self.plant.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.plant.name}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('PAID', 'Paid'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    items_json = models.TextField()  # store items as JSON
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_id = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    order_date = models.DateTimeField(default=timezone.now)
    state = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    # expected_delivery_date = models.DateField(
    # null=True,
    # blank=True,
    # help_text="Expected delivery date for this order."

    def items(self):
        try:
            return json.loads(self.items_json)
        except Exception:
            return []

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} <{self.email}>"


class Profile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"Profile for {self.user.username}"


class NotifyRequest(models.Model):
    """Users or visitors can request to be notified when a Plant is restocked."""
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name='notify_requests')
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)

    def __str__(self):
        return f"NotifyRequest for {self.plant.name} ({self.email or (self.user.username if self.user else 'anonymous')})"
    
# class OrderItem(models.Model):
#     order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='order_items', null=True, blank=True)
#     plant = models.ForeignKey('Plant', on_delete=models.CASCADE)
#     quantity = models.PositiveIntegerField(null=True, blank=True)
#     price = models.DecimalField(max_digits=8, decimal_places=2)

#     def __str__(self):
#         return f"{self.quantity} *{self.plant.name}"
# class OrderItem(models.Model):
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
#     plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name='sold_items')
#     quantity = models.PositiveIntegerField(default=1)

#     def __str__(self):
#         return f"{self.plant.name} ({self.quantity})"
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name='sold_items')
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.plant.name} ({self.quantity})"
