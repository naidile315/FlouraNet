from django.views.decorators.http import require_GET
import decimal

@require_GET
def revenue_chart_data(request):
    # Example: monthly revenue for last 6 months
    from django.utils import timezone
    from django.db.models import Sum
    from django.db.models.functions import TruncMonth
    now = timezone.now()
    start_month = now.month - 5
    start_year = now.year
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    start_date = timezone.datetime(start_year, start_month, 1, tzinfo=now.tzinfo)
    qs = (
        Order.objects.filter(status='PAID', order_date__gte=start_date)
        .annotate(month=TruncMonth('order_date'))
        .values('month')
        .annotate(total=Sum('total_amount'))
        .order_by('month')
    )
    labels = []
    data = []
    for entry in qs:
        m = entry.get('month')
        if m:
            labels.append(m.strftime('%b %Y'))
            val = entry.get('total') or 0
            if isinstance(val, decimal.Decimal):
                val = float(val)
            data.append(val)
    return JsonResponse({'labels': labels, 'data': data})
from django.shortcuts import render, get_object_or_404, redirect
from .models import Plant, Category, CartItem, Order
from django.db import models as djmodels
import csv
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from .forms import ContactForm, RegistrationForm, CheckoutForm, NotifyRequestForm
from .models import NotifyRequest
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import transaction
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import hmac
import hashlib
import importlib

# Try to import the optional `razorpay` package at runtime. If it's not
# installed the variable will be set to None and the code paths that rely
# on Razorpay will be skipped. Using importlib avoids some static-import
# errors in linters/analysers when the package isn't available in the
# environment.
try:
    razorpay = importlib.import_module('razorpay')
except Exception:
    razorpay = None


def home(request):
    categories = Category.objects.all()
    featured = Plant.objects.all()[:8]
    return render(request, 'home.html', {'categories': categories, 'featured': featured})


def shop(request):
    q = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    plants = Plant.objects.all().select_related('category')
    if category_filter:
        plants = plants.filter(category__name__iexact=category_filter)
    if q:
        plants = plants.filter(name__icontains=q) | plants.filter(category__name__icontains=q)
    categories = Category.objects.all()
    return render(request, 'shop.html', {
        'plants': plants,
        'categories': categories,
        'q': q,
        'selected_category': category_filter,
    })


def plant_detail(request, pk):
    plant = get_object_or_404(Plant, pk=pk)
    return render(request, 'plant_detail.html', {'plant': plant})


@login_required
def add_to_cart(request, pk):
    plant = get_object_or_404(Plant, pk=pk)
    item, created = CartItem.objects.get_or_create(user=request.user, plant=plant)
    if not created:
        item.quantity += 1
        item.save()
    messages.success(request, 'Added to cart')
    return redirect('nursery_app:view_cart')


@login_required
def view_cart(request):
    items = CartItem.objects.filter(user=request.user)
    total = sum([it.total_price for it in items])
    return render(request, 'cart.html', {'items': items, 'total': total})


@login_required
def remove_from_cart(request, pk):
    item = get_object_or_404(CartItem, pk=pk, user=request.user)
    item.delete()
    messages.success(request, 'Removed from cart')
    return redirect('nursery_app:view_cart')


@login_required
@require_POST
def update_cart_quantity(request):
    """AJAX endpoint to update a cart item's quantity and return updated totals."""
    try:
        data = json.loads(request.body.decode())
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    item_id = data.get('item_id')
    qty = data.get('quantity')
    if item_id is None or qty is None:
        return JsonResponse({'status': 'error', 'message': 'Missing parameters'}, status=400)
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Invalid quantity'}, status=400)
    if qty < 1:
        # treat as remove
        try:
            item = CartItem.objects.get(pk=item_id, user=request.user)
            item.delete()
        except CartItem.DoesNotExist:
            pass
        # recompute totals
        items = CartItem.objects.filter(user=request.user)
        total = sum([it.total_price for it in items])
        return JsonResponse({'status': 'ok', 'action': 'deleted', 'total': float(total)})
    try:
        item = CartItem.objects.get(pk=item_id, user=request.user)
    except CartItem.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Item not found'}, status=404)
    # update quantity and return updated totals
    item.quantity = qty
    item.save()
    items = CartItem.objects.filter(user=request.user)
    total = sum([it.total_price for it in items])
    return JsonResponse({'status': 'ok', 'item_total': float(item.total_price), 'total': float(total)})


@login_required
def checkout(request):
    items = CartItem.objects.filter(user=request.user)
    if not items.exists():
        messages.info(request, 'Your cart is empty')
        return redirect('nursery_app:shop')
    total = sum([it.total_price for it in items])
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Validate stock availability before creating an order
            for it in items:
                if it.quantity > it.plant.stock:
                    messages.error(request, f"Only {it.plant.stock} items of '{it.plant.name}' are available. Please adjust your order quantity.")
                    return redirect('nursery_app:view_cart')
            items_list = []
            for it in items:
                items_list.append({'plant': it.plant.name, 'qty': it.quantity, 'price': float(it.plant.price)})
            order = Order.objects.create(
                user=request.user,
                items_json=json.dumps(items_list),
                total_amount=total,
                status='PENDING',
                state=form.cleaned_data.get('state', ''),
                district=form.cleaned_data.get('district', '')
            )
            # If razorpay available and keys set, create a razorpay order and return details to client
            if razorpay and settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
                client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                rp_order = client.order.create({'amount': int(total * 100), 'currency': 'INR', 'payment_capture': 1})
                # Save razorpay order id to payment_id temporarily
                order.payment_id = rp_order.get('id')
                order.save()
                return render(request, 'checkout_payment.html', {'order': order, 'rp_order': rp_order, 'razorpay_key': settings.RAZORPAY_KEY_ID})
            else:
                # fallback simulated payment: decrement stock atomically and mark paid
                try:
                    with transaction.atomic():
                        # Lock plant rows and decrement
                        for it in items:
                            p = Plant.objects.select_for_update().get(pk=it.plant.pk)
                            if p.stock < it.quantity:
                                messages.error(request, f"Only {p.stock} items of '{p.name}' are available. Please adjust your order quantity.")
                                order.status = 'PENDING'
                                order.save()
                                return redirect('nursery_app:view_cart')
                            p.stock = p.stock - it.quantity
                            p.save()
                        # Use the payment id submitted by the user (e.g., UTR/txn id) when present;
                        # fall back to a default simulated id otherwise.
                        submitted_pid = request.POST.get('payment_id') if request else None
                        order.payment_id = submitted_pid or 'SIMULATED_TXN_12345'
                        order.status = 'PAID'
                        order.save()
                        items.delete()
                        return redirect('nursery_app:payment_success')
                except Exception as e:
                    messages.error(request, 'Payment processing failed')
                    return redirect('nursery_app:view_cart')
    else:
        form = CheckoutForm()
    return render(request, 'checkout.html', {'items': items, 'total': total, 'form': form})


def payment_success(request):
    # Show latest successful order for the user if available
    latest = None
    if request.user.is_authenticated:
        latest = Order.objects.filter(user=request.user, status='PAID').order_by('-order_date').first()
    return render(request, 'payment_success.html', {'order': latest})


def payment_failed(request):
    return render(request, 'payment_failed.html')


@csrf_exempt
def payment_verify(request):
    # Accept AJAX POST from client after payment and verify signature
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
    data = json.loads(request.body.decode())
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    # Find the order by payment id
    try:
        order = Order.objects.get(payment_id=razorpay_order_id)
    except Order.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Order not found'}, status=404)
    # Verify signature if possible
    if settings.RAZORPAY_KEY_SECRET and razorpay:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': 'Signature verification failed', 'error': str(e)}, status=400)
    # Mark order as paid and store payment id
    # Decrement stock atomically and mark order as paid
    try:
        with transaction.atomic():
            # Reload order and items to ensure consistency
            order.refresh_from_db()
            items = order.items()
            # items is a list of dicts with 'plant' names; map names to Plant objects
            # We stored names earlier; better to protect by matching by name and reducing stock.
            for it in items:
                pname = it.get('plant')
                qty = int(it.get('qty', 0))
                p = Plant.objects.select_for_update().get(name=pname)
                if p.stock < qty:
                    # insufficient stock; don't mark paid
                    return JsonResponse({'status': 'error', 'message': f"Insufficient stock for {p.name}"}, status=400)
                p.stock = p.stock - qty
                p.save()
            order.payment_id = razorpay_payment_id
            order.status = 'PAID'
            order.save()
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Could not finalize order', 'error': str(e)}, status=500)

    # Send confirmation email if email settings are configured and user has an email
    try:
        if settings.EMAIL_HOST and request.user.is_authenticated and request.user.email:
            send_mail(
                f'Order #{order.id} confirmation',
                f'Thank you for your order. Your payment was successful and your order #{order.id} is being processed.',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=True,
            )
    except Exception:
        # don't fail the request if email sending fails
        pass
    return JsonResponse({'status': 'ok', 'message': 'Payment verified'})


@csrf_exempt
def payment_webhook(request):
    """Razorpay webhook endpoint. Verifies HMAC signature using RAZORPAY_WEBHOOK_SECRET
    and updates the corresponding Order (by matching razorpay order id saved in payment_id).
    """
    secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
    if not secret:
        return JsonResponse({'status': 'error', 'message': 'Webhook secret not configured'}, status=400)
    body = request.body or b''
    signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE') or request.META.get('HTTP_X_RAZORPAY_SIGNATURE'.lower())
    if not signature:
        return JsonResponse({'status': 'error', 'message': 'Missing signature header'}, status=400)
    # compute expected signature
    expected = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=400)
    # parse payload and handle events
    try:
        payload = json.loads(body.decode('utf-8'))
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    # For payment events, try to extract razorpay_order_id
    rp_order_id = None
    try:
        # Try common paths
        rp_order_id = payload.get('payload', {}).get('payment', {}).get('entity', {}).get('order_id')
    except Exception:
        rp_order_id = None
    if not rp_order_id:
        # fallback: sometimes payload contains order info directly
        rp_order_id = payload.get('order_id') or payload.get('payload', {}).get('order', {}).get('entity', {}).get('id')
    if not rp_order_id:
        return JsonResponse({'status': 'error', 'message': 'No order id in payload'}, status=400)
    # Find corresponding orders and mark paid (handle duplicates by updating all)
    qs = Order.objects.filter(payment_id=rp_order_id)
    if not qs.exists():
        return JsonResponse({'status': 'error', 'message': 'Order not found'}, status=404)
    payment_id = None
    try:
        payment_id = payload.get('payload', {}).get('payment', {}).get('entity', {}).get('id')
    except Exception:
        payment_id = None
    update_kwargs = {'status': 'PAID'}
    if payment_id:
        update_kwargs['payment_id'] = payment_id
    qs.update(**update_kwargs)
    # After marking as PAID, decrement stock for affected orders
    if update_kwargs.get('status') == 'PAID':
        try:
            for order in qs:
                try:
                    with transaction.atomic():
                        items = order.items()
                        for it in items:
                            pname = it.get('plant')
                            qty = int(it.get('qty', 0))
                            p = Plant.objects.select_for_update().get(name=pname)
                            if p.stock >= qty:
                                p.stock = p.stock - qty
                                p.save()
                except Exception:
                    # ignore individual order stock update failures
                    pass
        except Exception:
            pass
    return JsonResponse({'status': 'ok'})


def order_history(request):
    if not request.user.is_authenticated:
        return render(request, 'orders.html', {'orders': [], 'is_guest': True})
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    return render(request, 'orders.html', {'orders': orders, 'is_guest': False})





def admin_dashboard(request):
    # Simple admin-like dashboard (requires staff or superuser check in prod)
    total_users = 0
    total_plants = Plant.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(status='PAID').aggregate(djmodels.Sum('total_amount'))['total_amount__sum'] or 0
    recent_orders = Order.objects.order_by('-order_date')[:5]
    total_stock = Plant.objects.aggregate(djmodels.Sum('stock'))['stock__sum'] or 0
    
    # Get time period from request
    period = request.GET.get('period', 'all')  # all, 6m, 3m, 1m
    from django.utils import timezone
    from django.db.models import Sum, Count
    from django.db.models.functions import TruncMonth
    import datetime
    now = timezone.now()
    # Determine available years from paid orders
    years_qs = Order.objects.filter(status='PAID').dates('order_date', 'year')
    years = sorted({d.year for d in years_qs}, reverse=True)
    selected_year = int(request.GET.get('year', now.year))

    # Calculate start date based on period
    start_date = None
    if period == '1m':
        start_date = (now - datetime.timedelta(days=30)).date()
    elif period == '3m':
        start_date = (now - datetime.timedelta(days=90)).date()
    elif period == '6m':
        start_date = (now - datetime.timedelta(days=180)).date()
    else:
        # Default to showing full year data
        start_date = datetime.date(selected_year, 1, 1)
    
    # Build month labels and data
    month_data = []
    current = start_date
    while current <= now.date():
        month_data.append({
            'date': current,
            'label': current.strftime('%b %Y')
        })
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    month_labels = [m['label'] for m in month_data]
    monthly_revenue = []
    monthly_order_counts = []
    
    # Find month with highest orders
    max_orders = 0
    max_orders_month = None
    
    for m in month_data:
        total = Order.objects.filter(
            status='PAID',
            order_date__year=m['date'].year,
            order_date__month=m['date'].month
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        cnt = Order.objects.filter(
            status='PAID',
            order_date__year=m['date'].year,
            order_date__month=m['date'].month
        ).count()
        
        if cnt > max_orders:
            max_orders = cnt
            max_orders_month = m['label']
        
        monthly_revenue.append(float(total))
        monthly_order_counts.append(int(cnt))

    # Category-wise sales and per-plant quantities for the selected year
    categories = {}
    paid_orders = Order.objects.filter(status='PAID', order_date__year=selected_year)
    for o in paid_orders:
        for it in o.items():
            pname = it.get('plant')
            qty = int(it.get('qty', 0))
            try:
                p = Plant.objects.get(name=pname)
                cat = p.category.name if p.category else 'Uncategorized'
                categories[cat] = categories.get(cat, 0) + (float(it.get('price', 0)) * qty)
            except Plant.DoesNotExist:
                continue

    cat_labels = list(categories.keys())
    cat_values = [float(categories[k]) for k in cat_labels]

    # Top-selling plants (by quantity) and full per-plant table
    plant_qty = {}
    for o in paid_orders:
        for it in o.items():
            pname = it.get('plant')
            qty = int(it.get('qty', 0))
            plant_qty[pname] = plant_qty.get(pname, 0) + qty
    top_plants = sorted(plant_qty.items(), key=lambda x: x[1], reverse=True)[:10]
    top_labels = [p[0] for p in top_plants]
    top_values = [p[1] for p in top_plants]
    # build plant rows for table (all plants sold in selected year)
    plant_rows = []
    for name, qty in sorted(plant_qty.items(), key=lambda x: x[1], reverse=True):
        try:
            p = Plant.objects.get(name=name)
            cat = p.category.name if p.category else ''
        except Plant.DoesNotExist:
            cat = ''
        plant_rows.append({'plant': name, 'qty': qty, 'category': cat})

    # Customer growth (registrations per month for last 12 months)
    from django.contrib.auth.models import User
    monthly_customers = []
    for i in range(11, -1, -1):
        start = (now - datetime.timedelta(days=now.day - 1)).replace(day=1) - datetime.timedelta(days=30 * i)
        end = (start + datetime.timedelta(days=31)).replace(day=1)
        cnt = User.objects.filter(date_joined__gte=start, date_joined__lt=end).count()
        monthly_customers.append(cnt)

    return render(request, 'admin_dashboard.html', {
        'total_plants': total_plants,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_stock': total_stock,
        'recent_orders': recent_orders,
        'years': years,
        'selected_year': selected_year,
        'period': period,
        'month_labels': month_labels,
        'monthly_revenue': monthly_revenue,
        'cat_labels': cat_labels,
        'cat_values': cat_values,
        'top_labels': top_labels,
        'top_values': top_values,
        'monthly_customers': monthly_customers,
        'monthly_order_counts': monthly_order_counts,
        'plant_rows': plant_rows,
        'max_orders_month': max_orders_month,
        'max_orders': max_orders,
    })


@staff_member_required
def export_plant_sales_csv(request):
    """Export per-plant sales for a given year as CSV. Requires staff.

    Query param: year (defaults to current year)
    """
    from django.utils import timezone
    year = int(request.GET.get('year', timezone.now().year))
    qs = Order.objects.filter(status='PAID', order_date__year=year)

    # aggregate quantities and revenue by plant name
    plant_stats = {}
    for o in qs:
        for it in o.items():
            pname = it.get('plant')
            try:
                qty = int(it.get('qty', 0))
            except Exception:
                qty = 0
            try:
                price = float(it.get('price', 0))
            except Exception:
                price = 0.0
            stat = plant_stats.get(pname, {'qty': 0, 'revenue': 0.0})
            stat['qty'] += qty
            stat['revenue'] += (price * qty)
            plant_stats[pname] = stat

    # build response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="plant_sales_{year}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Plant', 'Category', 'Quantity', 'Revenue'])

    for name, data in sorted(plant_stats.items(), key=lambda x: x[1]['qty'], reverse=True):
        qty = data['qty']
        rev = data['revenue']
        try:
            p = Plant.objects.get(name=name)
            cat = p.category.name if p.category else ''
        except Plant.DoesNotExist:
            cat = ''
        writer.writerow([name, cat, qty, ('%.2f' % rev)])

    return response


@staff_member_required
def export_yearly_revenue_csv(request):
    """Export monthly revenue for a selected year as CSV."""
    from django.utils import timezone
    year = int(request.GET.get('year', timezone.now().year))
    # Build monthly totals
    import calendar
    months = list(range(1, 13))
    monthly_totals = []
    for m in months:
        tot = Order.objects.filter(status='PAID', order_date__year=year, order_date__month=m).aggregate(djmodels.Sum('total_amount'))['total_amount__sum'] or 0
        monthly_totals.append(float(tot))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="yearly_revenue_{year}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Month', 'Revenue'])
    for m, val in zip(months, monthly_totals):
        writer.writerow([calendar.month_name[m], ('%.2f' % val)])
    return response


@staff_member_required
def export_matrix_csv(request):
    """Export a plant vs months matrix for the selected year.

    Columns: Plant, Category, Jan..Dec, Total_Qty, Total_Revenue
    """
    from django.utils import timezone
    year = int(request.GET.get('year', timezone.now().year))
    qs = Order.objects.filter(status='PAID', order_date__year=year)

    # build plant -> months stats
    plant_map = {}
    for o in qs:
        m = o.order_date.month
        for it in o.items():
            pname = it.get('plant')
            try:
                qty = int(it.get('qty', 0))
            except Exception:
                qty = 0
            try:
                price = float(it.get('price', 0))
            except Exception:
                price = 0.0
            entry = plant_map.get(pname)
            if not entry:
                entry = {'months': [0]*12, 'total_qty': 0, 'total_revenue': 0.0}
            entry['months'][m-1] += qty
            entry['total_qty'] += qty
            entry['total_revenue'] += (qty * price)
            plant_map[pname] = entry

    # prepare response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="plant_matrix_{year}.csv"'
    writer = csv.writer(response)
    header = ['Plant', 'Category'] + [ 'Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec' ] + ['Total_Qty','Total_Revenue']
    writer.writerow(header)

    for name, data in sorted(plant_map.items(), key=lambda x: x[1]['total_qty'], reverse=True):
        try:
            p = Plant.objects.get(name=name)
            cat = p.category.name if p.category else ''
        except Plant.DoesNotExist:
            cat = ''
        row = [name, cat] + data['months'] + [data['total_qty'], ('%.2f' % data['total_revenue'])]
        writer.writerow(row)
    return response


@staff_member_required
def export_orders_csv(request):
    """Export order-level CSV for the selected year (one row per order).

    Columns: OrderID, User, Date, TotalAmount, PaymentID, State, District, Items
    """
    from django.utils import timezone
    year = int(request.GET.get('year', timezone.now().year))
    qs = Order.objects.filter(order_date__year=year).order_by('order_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="orders_{year}.csv"'
    writer = csv.writer(response)
    writer.writerow(['OrderID','User','Date','TotalAmount','PaymentID','State','District','ItemsJSON'])
    for o in qs:
        user = o.user.username if o.user else ''
        date = o.order_date.isoformat()
        items_str = o.items_json.replace('\n', ' ')
        writer.writerow([o.id, user, date, ('%.2f' % float(o.total_amount)), o.payment_id or '', o.state or '', o.district or '', items_str])
    return response


def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Message sent')
            return redirect('nursery_app:contact')
    else:
        form = ContactForm()
    return render(request, 'contact.html', {'form': form})


def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            # save phone to profile if provided
            phone = form.cleaned_data.get('phone')
            try:
                profile = user.profile
            except Exception:
                from .models import Profile
                profile = Profile.objects.create(user=user)
            if phone:
                profile.phone = phone
                profile.save()
            messages.success(request, 'Registration successful. Please log in.')
            return redirect('nursery_app:login')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('nursery_app:home')
        else:
            messages.error(request, 'Invalid credentials')
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('nursery_app:home')


@require_POST
def notify_request(request):
    """Create a NotifyRequest for a given plant id POSTed as 'plant_id'."""
    form = NotifyRequestForm(request.POST)
    plant_id = request.POST.get('plant_id')
    if not plant_id:
        return JsonResponse({'status': 'error', 'message': 'Missing plant_id'}, status=400)
    try:
        plant = Plant.objects.get(pk=plant_id)
    except Plant.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Plant not found'}, status=404)
    if form.is_valid():
        email = form.cleaned_data.get('email')
        nr = NotifyRequest.objects.create(plant=plant, user=(request.user if request.user.is_authenticated else None), email=email or '')
        return JsonResponse({'status': 'ok', 'message': 'We will notify you when this item is back in stock'})
    return JsonResponse({'status': 'error', 'message': 'Invalid data'}, status=400)
