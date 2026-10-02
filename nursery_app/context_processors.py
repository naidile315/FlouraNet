from .models import Category, CartItem

def nursery_context(request):
    try:
        categories = Category.objects.all()
    except Exception:
        categories = []
    
    cart_count = 0
    if request.user.is_authenticated:
        try:
            cart_count = sum(item.quantity for item in CartItem.objects.filter(user=request.user))
        except Exception:
            cart_count = 0
            
    return {
        'nav_categories': categories,
        'cart_count': cart_count,
    }
