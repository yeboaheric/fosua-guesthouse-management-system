import csv
import json
import logging
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.deletion import ProtectedError
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from accounts.decorators import group_required
from accounts.permissions import user_is_admin_role
from accounts.reporting import (
    completed_pos_sales_queryset,
    normalize_date_range,
    pos_sales_total,
    report_window_for_period as shared_report_window_for_period,
)
from inventory.forms import (
    InventoryCategoryForm,
    InventoryItemForm,
    InventorySubcategoryForm,
    POSCheckoutForm,
    SaleEditForm,
    StockAdjustmentForm,
    SupplierForm,
)
from inventory.models import (
    InventoryCategory,
    InventoryItem,
    InventorySubcategory,
    InventoryTransaction,
    Sale,
    SaleItem,
    StockAdjustment,
    Supplier,
)

ZERO_MONEY = Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2))
ZERO_UNITS = Value(Decimal("0.000"), output_field=DecimalField(max_digits=12, decimal_places=3))
logger = logging.getLogger(__name__)


def _inventory_xlsx_response(workbook, filename):
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _user_can_edit_sale(user):
    return user_is_admin_role(user)


@group_required("Admin", "Receptionist", module="inventory")
def inventory_dashboard(request):
    today = timezone.localdate()
    month_start, month_end = shared_report_window_for_period("monthly", today)
    items = InventoryItem.objects.select_related("category", "subcategory", "supplier")
    sales = Sale.objects.filter(status=Sale.SaleStatus.COMPLETED)
    transactions = InventoryTransaction.objects.select_related("item", "created_by").order_by("-created_at")

    inventory_value = items.annotate(
        line_value=F("purchase_price") * F("quantity_in_stock")
    ).aggregate(
        total=Coalesce(
            Sum("line_value"),
            ZERO_MONEY,
        )
    )["total"]

    sales_today_total = pos_sales_total(today, today)
    sales_month_total = pos_sales_total(month_start, month_end)

    recent_sales = sales.select_related("cashier").prefetch_related("items__item")[:8]
    recent_transactions = transactions[:10]
    low_stock_items = items.filter(quantity_in_stock__lte=F("minimum_stock_threshold"))
    out_of_stock_items = items.filter(quantity_in_stock__lte=0)

    daily_sales_rows = _daily_sales_rows(today - timedelta(days=6), today)
    category_rows = (
        SaleItem.objects.values("item__category__name")
        .annotate(total_units=Coalesce(Sum("quantity"), ZERO_UNITS))
        .order_by("-total_units")[:6]
    )

    return render(
        request,
        "inventory/dashboard.html",
        {
            "today": today,
            "categories_count": InventoryCategory.objects.count(),
            "subcategories_count": InventorySubcategory.objects.count(),
            "suppliers_count": Supplier.objects.count(),
            "items_count": items.count(),
            "low_stock_count": low_stock_items.count(),
            "out_of_stock_count": out_of_stock_items.count(),
            "inventory_value": inventory_value,
            "sales_today_total": sales_today_total,
            "sales_month_total": sales_month_total,
            "recent_sales": recent_sales,
            "recent_transactions": recent_transactions,
            "low_stock_items": low_stock_items[:8],
            "daily_labels_json": json.dumps([row["date"] for row in daily_sales_rows]),
            "daily_sales_json": json.dumps([float(row["total"]) for row in daily_sales_rows]),
            "category_labels_json": json.dumps([row["item__category__name"] or "Uncategorised" for row in category_rows]),
            "category_units_json": json.dumps([float(row["total_units"]) for row in category_rows]),
        },
    )


@group_required("Admin", "Receptionist", module="inventory")
def category_list(request):
    form = InventoryCategoryForm()
    if request.method == "POST":
        form = InventoryCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category created successfully.")
            return redirect("inventory-categories")
    categories = InventoryCategory.objects.annotate(item_count=Count("items")).order_by("category_group", "name")
    return render(request, "inventory/category_list.html", {"form": form, "categories": categories})


@group_required("Admin", "Receptionist", module="inventory")
def category_update(request, pk):
    category = get_object_or_404(InventoryCategory, pk=pk)
    form = InventoryCategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Category updated successfully.")
        return redirect("inventory-categories")
    return render(request, "inventory/entity_form.html", {"form": form, "title": "Edit Category"})


@require_POST
@group_required("Admin", "Receptionist", module="inventory")
def category_delete(request, pk):
    category = get_object_or_404(InventoryCategory, pk=pk)
    try:
        category.delete()
        messages.success(request, "Category deleted.")
    except ProtectedError:
        messages.error(request, "This category is in use and cannot be deleted.")
    return redirect("inventory-categories")


@group_required("Admin", "Receptionist", module="inventory")
def subcategory_list(request):
    form = InventorySubcategoryForm()
    if request.method == "POST":
        form = InventorySubcategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Subcategory created successfully.")
            return redirect("inventory-subcategories")
    subcategories = InventorySubcategory.objects.select_related("category").annotate(
        item_count=Count("items")
    )
    return render(request, "inventory/subcategory_list.html", {"form": form, "subcategories": subcategories})


@group_required("Admin", "Receptionist", module="inventory")
def subcategory_update(request, pk):
    subcategory = get_object_or_404(InventorySubcategory, pk=pk)
    form = InventorySubcategoryForm(request.POST or None, instance=subcategory)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Subcategory updated successfully.")
        return redirect("inventory-subcategories")
    return render(request, "inventory/entity_form.html", {"form": form, "title": "Edit Subcategory"})


@require_POST
@group_required("Admin", "Receptionist", module="inventory")
def subcategory_delete(request, pk):
    subcategory = get_object_or_404(InventorySubcategory, pk=pk)
    try:
        subcategory.delete()
        messages.success(request, "Subcategory deleted.")
    except ProtectedError:
        messages.error(request, "This subcategory is in use and cannot be deleted.")
    return redirect("inventory-subcategories")


@group_required("Admin", "Receptionist", module="inventory")
def supplier_list(request):
    form = SupplierForm()
    if request.method == "POST":
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Supplier created successfully.")
            return redirect("inventory-suppliers")
    suppliers = Supplier.objects.annotate(item_count=Count("items")).order_by("name")
    return render(request, "inventory/supplier_list.html", {"form": form, "suppliers": suppliers})


@group_required("Admin", "Receptionist", module="inventory")
def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    form = SupplierForm(request.POST or None, instance=supplier)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Supplier updated successfully.")
        return redirect("inventory-suppliers")
    return render(request, "inventory/entity_form.html", {"form": form, "title": "Edit Supplier"})


@require_POST
@group_required("Admin", "Receptionist", module="inventory")
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    try:
        supplier.delete()
        messages.success(request, "Supplier deleted.")
    except ProtectedError:
        messages.error(request, "This supplier is linked to items and cannot be deleted.")
    return redirect("inventory-suppliers")


@group_required("Admin", "Receptionist", module="inventory")
def item_list(request):
    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    subcategory_id = request.GET.get("subcategory", "")
    supplier_id = request.GET.get("supplier", "")
    stock_status = request.GET.get("stock", "")

    items = InventoryItem.objects.select_related("category", "subcategory", "supplier").order_by("category__name", "name")
    if query:
        items = items.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
            | Q(subcategory__name__icontains=query)
            | Q(supplier__name__icontains=query)
        )
    if category_id:
        items = items.filter(category_id=category_id)
    if subcategory_id:
        items = items.filter(subcategory_id=subcategory_id)
    if supplier_id:
        items = items.filter(supplier_id=supplier_id)
    if stock_status == "low":
        items = items.filter(quantity_in_stock__lte=F("minimum_stock_threshold"))
    elif stock_status == "out":
        items = items.filter(quantity_in_stock__lte=0)
    elif stock_status == "in":
        items = items.filter(quantity_in_stock__gt=F("minimum_stock_threshold"))

    if request.GET.get("export") == "stock_xlsx":
        from openpyxl import Workbook
        from openpyxl.styles import Font

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Stock List"
        worksheet.append(["Item Name", "Quantity in Stock"])
        for cell in worksheet[1]:
            cell.font = Font(bold=True)
        for item in items:
            quantity = Decimal(item.quantity_in_stock or 0)
            worksheet.append(
                [
                    item.name,
                    int(quantity) if quantity == quantity.to_integral_value() else float(quantity),
                ]
            )
        worksheet.column_dimensions["A"].width = 36
        worksheet.column_dimensions["B"].width = 18
        for row in worksheet.iter_rows(min_row=2, min_col=2, max_col=2):
            for cell in row:
                cell.number_format = "0.###"
        return _inventory_xlsx_response(
            workbook,
            f"inventory-stock-list-{timezone.localdate().strftime('%d-%m-%Y')}.xlsx",
        )

    export_params = request.GET.copy()
    export_params["export"] = "stock_xlsx"

    context = {
        "items": items,
        "query": query,
        "categories": InventoryCategory.objects.all(),
        "subcategories": InventorySubcategory.objects.select_related("category").all(),
        "suppliers": Supplier.objects.all(),
        "selected_category": category_id,
        "selected_subcategory": subcategory_id,
        "selected_supplier": supplier_id,
        "selected_stock": stock_status,
        "low_stock_count": items.filter(quantity_in_stock__lte=F("minimum_stock_threshold")).count(),
        "out_of_stock_count": items.filter(quantity_in_stock__lte=0).count(),
        "stock_export_query": export_params.urlencode(),
    }
    return render(request, "inventory/item_list.html", context)


@group_required("Admin", "Receptionist", module="inventory")
def item_create(request):
    form = InventoryItemForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        _record_opening_stock(item, request.user)
        messages.success(request, "Inventory item created.")
        return redirect("inventory-items")
    return render(request, "inventory/item_form.html", {"form": form, "title": "New Inventory Item"})


@group_required("Admin", "Receptionist", module="inventory")
def item_update(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    previous_quantity = item.quantity_in_stock
    form = InventoryItemForm(request.POST or None, request.FILES or None, instance=item)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        if item.quantity_in_stock != previous_quantity:
            _log_transaction(
                item=item,
                quantity_before=previous_quantity,
                quantity_changed=item.quantity_in_stock - previous_quantity,
                quantity_after=item.quantity_in_stock,
                transaction_type=InventoryTransaction.TransactionType.ADJUSTMENT,
                created_by=request.user,
                reference=item.name,
                notes="Manual stock update from item edit.",
            )
        messages.success(request, "Inventory item updated.")
        return redirect("inventory-items")
    return render(request, "inventory/item_form.html", {"form": form, "title": "Edit Inventory Item"})


@require_POST
@group_required("Admin", "Receptionist", module="inventory")
def item_delete(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    try:
        with transaction.atomic():
            if item.sale_items.exists():
                raise ProtectedError("sale-linked inventory item", [item])
            item.transactions.all().delete()
            item.adjustments.all().delete()
            item.delete()
        messages.success(request, "Inventory item deleted.")
    except ProtectedError:
        messages.error(request, "This item is linked to stock history or sales and cannot be deleted.")
    return redirect("inventory-items")


@group_required("Admin", "Receptionist", module="inventory")
def item_adjust_stock(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    form = StockAdjustmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        previous_quantity = item.quantity_in_stock
        new_quantity = form.cleaned_data["quantity"]
        item.quantity_in_stock = new_quantity
        item.save()
        adjustment = StockAdjustment.objects.create(
            item=item,
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            reason=form.cleaned_data["reason"],
            notes=form.cleaned_data["notes"],
            adjusted_by=request.user,
        )
        _log_transaction(
            item=item,
            quantity_before=previous_quantity,
            quantity_changed=new_quantity - previous_quantity,
            quantity_after=new_quantity,
            transaction_type=InventoryTransaction.TransactionType.ADJUSTMENT,
            created_by=request.user,
            stock_adjustment=adjustment,
            reference=item.name,
            notes=form.cleaned_data["notes"] or form.cleaned_data["reason"],
        )
        messages.success(request, "Stock adjusted successfully.")
        return redirect("inventory-items")
    return render(request, "inventory/adjustment_form.html", {"form": form, "item": item, "title": "Adjust Stock"})


@group_required("Admin", "Receptionist", module="inventory")
def transaction_list(request):
    query = request.GET.get("q", "").strip()
    tx_type = request.GET.get("type", "")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")
    transactions = InventoryTransaction.objects.select_related("item", "created_by", "sale", "stock_adjustment")
    if query:
        transactions = transactions.filter(
            Q(item__name__icontains=query)
            | Q(reference__icontains=query)
            | Q(notes__icontains=query)
            | Q(created_by__username__icontains=query)
        )
    if tx_type:
        transactions = transactions.filter(transaction_type=tx_type)
    if start_date:
        transactions = transactions.filter(created_at__date__gte=start_date)
    if end_date:
        transactions = transactions.filter(created_at__date__lte=end_date)
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="inventory-transactions.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Transaction",
            "Item",
            "Quantity Before",
            "Quantity Changed",
            "Quantity After",
            "Type",
            "Reference",
            "User",
            "Date Time",
            "Notes",
        ])
        for transaction_row in transactions[:1000]:
            writer.writerow([
                transaction_row.pk,
                transaction_row.item.name,
                transaction_row.quantity_before,
                transaction_row.quantity_changed,
                transaction_row.quantity_after,
                transaction_row.get_transaction_type_display(),
                transaction_row.reference,
                transaction_row.created_by.get_username() if transaction_row.created_by else "",
                timezone.localtime(transaction_row.created_at).strftime("%d/%m/%Y %H:%M"),
                transaction_row.notes,
            ])
        return response
    return render(
        request,
        "inventory/transaction_list.html",
        {
            "transactions": transactions[:50],
            "query": query,
            "type_choices": InventoryTransaction.TransactionType.choices,
            "selected_type": tx_type,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


def _pos_terminal_context(request, checkout_form, items=None, query=None, category_id=None):
    if items is None:
        items = InventoryItem.objects.select_related("category", "subcategory", "supplier").filter(is_active=True)
    if query is None:
        query = request.GET.get("q", "").strip()
    if category_id is None:
        category_id = request.GET.get("category", "")
    pos_sale_completed = request.GET.get("sale_success") == "1"
    sale_id = request.GET.get("sale_id", "").strip()
    pos_completed_sale = None
    if pos_sale_completed and sale_id.isdigit():
        pos_completed_sale = Sale.objects.only("pk", "receipt_number").filter(pk=int(sale_id)).first()
    return {
        "items": items[:100],
        "categories": InventoryCategory.objects.all(),
        "query": query,
        "selected_category": category_id,
        "checkout_form": checkout_form,
        "pos_sale_completed": pos_sale_completed,
        "pos_completed_sale": pos_completed_sale,
        "pos_reset_delay_ms": 1800,
    }


@group_required("Admin", "Receptionist", module="pos")
def pos_terminal(request):
    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    items = InventoryItem.objects.select_related("category", "subcategory", "supplier").filter(is_active=True)
    if query:
        items = items.filter(
            Q(name__icontains=query)
            | Q(category__name__icontains=query)
            | Q(subcategory__name__icontains=query)
        )
    if category_id:
        items = items.filter(category_id=category_id)
    return render(
        request,
        "inventory/pos_terminal.html",
        _pos_terminal_context(request, POSCheckoutForm(), items=items, query=query, category_id=category_id),
    )


@require_POST
@group_required("Admin", "Receptionist", module="pos")
def pos_checkout(request):
    form = POSCheckoutForm(request.POST)
    if not form.is_valid():
        return render(request, "inventory/pos_terminal.html", _pos_terminal_context(request, form), status=400)

    try:
        cart = json.loads(form.cleaned_data["cart"])
    except json.JSONDecodeError:
        form.add_error("cart", "Cart data is invalid.")
        return render(request, "inventory/pos_terminal.html", _pos_terminal_context(request, form), status=400)

    logger.debug("POS checkout cart content: %s", cart)

    if not cart:
        form.add_error("cart", "Cart is empty.")
        return render(request, "inventory/pos_terminal.html", _pos_terminal_context(request, form), status=400)

    try:
        with transaction.atomic():
            item_ids = [line["id"] for line in cart]
            items_by_id = {
                item.pk: item
                for item in InventoryItem.objects.filter(pk__in=item_ids)
            }
            missing_ids = [line["id"] for line in cart if line["id"] not in items_by_id]
            if missing_ids:
                raise ValidationError("One of the selected items no longer exists.")

            sale = None
            receipt_number = Sale.generate_receipt_number()
            for _ in range(5):
                try:
                    sale = Sale.objects.create(
                        cashier=request.user,
                        receipt_number=receipt_number,
                        payment_method=form.cleaned_data["payment_method"],
                        tax_amount=form.cleaned_data.get("tax_amount") or Decimal("0.00"),
                        discount_amount=form.cleaned_data.get("discount_amount") or Decimal("0.00"),
                        notes=form.cleaned_data.get("notes", ""),
                    )
                    break
                except IntegrityError:
                    receipt_number = Sale.generate_receipt_number()
            if sale is None:
                raise IntegrityError("Unable to generate a unique receipt number.")

            subtotal = Decimal("0.00")
            for line in cart:
                item = items_by_id[line["id"]]
                quantity = Decimal(str(line.get("quantity", "0")))
                if quantity <= 0:
                    raise ValidationError("Cart quantities must be greater than zero.")
                if item.quantity_in_stock < quantity:
                    raise ValidationError(f"Not enough stock for {item.name}.")

                line_total = (item.selling_price * quantity).quantize(Decimal("0.01"))
                subtotal += line_total
                previous_quantity = item.quantity_in_stock
                item.quantity_in_stock = previous_quantity - quantity
                item.save(update_fields=["quantity_in_stock", "updated_at"])
                SaleItem.objects.create(
                    sale=sale,
                    item=item,
                    quantity=quantity,
                    unit_price=item.selling_price,
                    line_total=line_total,
                )
                _log_transaction(
                    item=item,
                    quantity_before=previous_quantity,
                    quantity_changed=-quantity,
                    quantity_after=item.quantity_in_stock,
                    transaction_type=InventoryTransaction.TransactionType.SALE,
                    created_by=request.user,
                    sale=sale,
                    reference=sale.receipt_number,
                    notes=form.cleaned_data.get("notes", ""),
                )

            tax_amount = form.cleaned_data.get("tax_amount") or Decimal("0.00")
            discount_amount = form.cleaned_data.get("discount_amount") or Decimal("0.00")
            grand_total = (subtotal + tax_amount - discount_amount).quantize(Decimal("0.01"))
            amount_paid = form.cleaned_data.get("amount_paid") or grand_total

            sale.subtotal = subtotal.quantize(Decimal("0.01"))
            sale.grand_total = grand_total
            sale.amount_paid = amount_paid
            sale.change_due = max(amount_paid - grand_total, Decimal("0.00"))
            sale.save(update_fields=[
                "subtotal",
                "grand_total",
                "amount_paid",
                "change_due",
                "tax_amount",
                "discount_amount",
                "updated_at",
                "receipt_number",
            ])
    except Exception as exc:
        logger.exception("POS checkout failed for user %s with cart %s", request.user, cart)
        if isinstance(exc, ValidationError):
            message = "; ".join(exc.messages) if getattr(exc, "messages", None) else "Unable to complete sale."
        elif isinstance(exc, InvalidOperation):
            message = "Sale values are invalid. Please check item quantities and amounts."
        elif isinstance(exc, IntegrityError):
            message = "A database error occurred while completing the sale. Please try again."
        else:
            message = "Unable to complete sale. Please refresh and try again."
        form.add_error(None, message)
        return render(request, "inventory/pos_terminal.html", _pos_terminal_context(request, form), status=400)

    messages.success(request, f"Sale completed successfully. Receipt {sale.receipt_number} generated.")
    return redirect(f"{reverse('inventory-pos')}?sale_success=1&sale_id={sale.pk}")


@group_required("Admin", "Receptionist", module="pos")
def sale_list(request):
    query = request.GET.get("q", "").strip()
    payment_method = request.GET.get("method", "")
    sales = Sale.objects.select_related("cashier").order_by("-created_at")
    if query:
        sales = sales.filter(
            Q(receipt_number__icontains=query)
            | Q(customer_name__icontains=query)
            | Q(customer_phone__icontains=query)
            | Q(customer_email__icontains=query)
            | Q(items__item__name__icontains=query)
        ).distinct()
    if payment_method:
        sales = sales.filter(payment_method=payment_method)
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="pos-sales.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Receipt Number",
            "Customer",
            "Phone",
            "Email",
            "Payment Method",
            "Subtotal",
            "Tax",
            "Discount",
            "Grand Total",
            "Paid",
            "Change Due",
            "Cashier",
            "Date Time",
        ])
        for sale in sales[:1000]:
            writer.writerow([
                sale.receipt_number,
                sale.customer_name,
                sale.customer_phone,
                sale.customer_email,
                sale.get_payment_method_display(),
                sale.subtotal,
                sale.tax_amount,
                sale.discount_amount,
                sale.grand_total,
                sale.amount_paid,
                sale.change_due,
                sale.cashier.get_username() if sale.cashier else "",
                timezone.localtime(sale.created_at).strftime("%d/%m/%Y %H:%M"),
            ])
        return response
    return render(
        request,
        "inventory/sale_list.html",
        {
            "sales": sales[:50],
            "query": query,
            "payment_method": payment_method,
            "payment_methods": Sale.PaymentMethod.choices,
            "can_edit_sale": _user_can_edit_sale(request.user),
        },
    )


@group_required("Admin", "Receptionist", module="pos")
def sale_detail(request, pk):
    sale = get_object_or_404(Sale.objects.select_related("cashier"), pk=pk)
    items = sale.items.select_related("item")
    return render(
        request,
        "inventory/sale_detail.html",
        {
            "sale": sale,
            "items": items,
            "can_edit_sale": _user_can_edit_sale(request.user),
        },
    )


@group_required("Admin", "Receptionist", module="pos")
def sale_update(request, pk):
    sale = get_object_or_404(Sale.objects.select_related("cashier"), pk=pk)
    if not _user_can_edit_sale(request.user):
        messages.error(request, "Access Denied: You are not authorized to manage POS sales.")
        return redirect("inventory-sale-detail", pk=sale.pk)

    form = SaleEditForm(request.POST or None, instance=sale)
    if request.method == "POST" and form.is_valid():
        updated_sale = form.save(commit=False)
        subtotal = sale.items.aggregate(total=Coalesce(Sum("line_total"), ZERO_MONEY))["total"]
        gross_total = subtotal + (updated_sale.tax_amount or Decimal("0.00")) - (updated_sale.discount_amount or Decimal("0.00"))
        updated_sale.subtotal = subtotal.quantize(Decimal("0.01"))
        updated_sale.grand_total = max(gross_total, Decimal("0.00")).quantize(Decimal("0.01"))
        updated_sale.save()
        messages.success(request, f"Sale {sale.receipt_number} updated successfully.")
        return redirect("inventory-sale-detail", pk=sale.pk)

    return render(
        request,
        "inventory/sale_form.html",
        {
            "form": form,
            "sale": sale,
            "title": "Edit POS Sale",
        },
    )


@require_POST
@group_required("Admin", "Receptionist", module="pos")
def sale_delete(request, pk):
    sale = get_object_or_404(Sale.objects.prefetch_related("items__item", "transactions"), pk=pk)
    if not _user_can_edit_sale(request.user):
        messages.error(request, "Access Denied: You are not authorized to manage POS sales.")
        return redirect("inventory-sale-detail", pk=sale.pk)

    with transaction.atomic():
        for line in sale.items.select_related("item"):
            item = line.item
            item.quantity_in_stock = (item.quantity_in_stock or Decimal("0.000")) + line.quantity
            item.save()
        sale.transactions.all().delete()
        sale.delete()

    messages.success(request, "Sale deleted successfully.")
    return redirect("inventory-sales")


@group_required("Admin", "Receptionist", module="pos")
def sale_pdf(request, pk):
    sale = get_object_or_404(Sale.objects.select_related("cashier"), pk=pk)
    pdf_data = _render_sale_pdf(sale)
    response = HttpResponse(pdf_data, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{sale.receipt_number}.pdf"'
    return response


@group_required("Admin", "Receptionist", module="pos")
def sale_email(request, pk):
    sale = get_object_or_404(Sale.objects.select_related("cashier"), pk=pk)
    if not sale.customer_email:
        messages.error(request, "This sale does not have a customer email on file.")
        return redirect("inventory-sale-detail", pk=sale.pk)

    email = EmailMessage(
        subject=f"Fosua Guesthouse Receipt {sale.receipt_number}",
        body=(
            f"Dear {sale.customer_name or 'Customer'},\n\n"
            "Please find your receipt attached from Fosua Guesthouse - Aduman.\n"
        ),
        to=[sale.customer_email],
    )
    email.attach(f"{sale.receipt_number}.pdf", _render_sale_pdf(sale), "application/pdf")
    email.send(fail_silently=False)
    messages.success(request, f"Receipt sent to {sale.customer_email}.")
    return redirect("inventory-sale-detail", pk=sale.pk)


@group_required("Admin", "Receptionist", module="inventory")
def reports_center(request):
    period = request.GET.get("period", "month")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    range_start, range_end = _resolve_period(period, start_date, end_date)

    sales = completed_pos_sales_queryset(range_start, range_end)
    transactions = InventoryTransaction.objects.filter(created_at__date__range=[range_start, range_end])
    top_items = (
        SaleItem.objects.filter(sale__in=sales)
        .values("item__name")
        .annotate(total_units=Sum("quantity"), total_revenue=Sum("line_total"))
        .order_by("-total_units")[:10]
    )
    low_stock_items = InventoryItem.objects.select_related("category", "subcategory").filter(
        quantity_in_stock__lte=F("minimum_stock_threshold")
    )
    out_of_stock_items = InventoryItem.objects.filter(quantity_in_stock__lte=0)
    chart_rows = _daily_sales_rows(range_start, range_end)

    return render(
        request,
        "inventory/report_center.html",
        {
            "period": period,
            "start_date": range_start,
            "end_date": range_end,
            "sales_total": pos_sales_total(range_start, range_end),
            "sales_count": sales.count(),
            "transaction_count": transactions.count(),
            "inventory_value": InventoryItem.objects.annotate(
                line_value=F("purchase_price") * F("quantity_in_stock")
            ).aggregate(total=Coalesce(Sum("line_value"), ZERO_MONEY))["total"],
            "top_items": top_items,
            "low_stock_items": low_stock_items[:10],
            "out_of_stock_items": out_of_stock_items[:10],
            "chart_labels_json": json.dumps([row["date"] for row in chart_rows]),
            "chart_values_json": json.dumps([float(row["total"]) for row in chart_rows]),
        },
    )


def _record_opening_stock(item, user):
    if item.quantity_in_stock <= 0:
        return
    _log_transaction(
        item=item,
        quantity_before=Decimal("0.000"),
        quantity_changed=item.quantity_in_stock,
        quantity_after=item.quantity_in_stock,
        transaction_type=InventoryTransaction.TransactionType.PURCHASE,
        created_by=user,
        reference=item.name,
        notes="Opening stock recorded when item was created.",
    )


def _log_transaction(
    *,
    item,
    quantity_before,
    quantity_changed,
    quantity_after,
    transaction_type,
    created_by,
    reference="",
    notes="",
    sale=None,
    stock_adjustment=None,
):
    InventoryTransaction.objects.create(
        item=item,
        sale=sale,
        stock_adjustment=stock_adjustment,
        quantity_before=quantity_before,
        quantity_changed=quantity_changed,
        quantity_after=quantity_after,
        transaction_type=transaction_type,
        reference=reference,
        notes=notes,
        created_by=created_by,
    )


def _resolve_period(period, start_date, end_date):
    today = timezone.localdate()
    if start_date and end_date:
        return normalize_date_range(date.fromisoformat(start_date), date.fromisoformat(end_date))
    if period == "day":
        return today, today
    if period == "week":
        return shared_report_window_for_period("weekly", today)
    if period == "year":
        year_start, _ = shared_report_window_for_period("yearly", today)
        return year_start, today
    if period == "custom":
        return today - timedelta(days=29), today
    month_start, _ = shared_report_window_for_period("monthly", today)
    return month_start, today


def _daily_sales_rows(start_date, end_date):
    rows = (
        completed_pos_sales_queryset(start_date, end_date)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Coalesce(Sum("grand_total"), ZERO_MONEY))
        .order_by("day")
    )
    values_by_day = {row["day"]: row["total"] for row in rows}
    current = start_date
    chart_rows = []
    while current <= end_date:
        chart_rows.append({"date": current.strftime("%b %d"), "total": values_by_day.get(current, 0)})
        current += timedelta(days=1)
    return chart_rows


def _render_sale_pdf(sale):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    logo_path = Path(settings.BASE_DIR) / "static" / "branding" / "fosua-logo.jpg"

    pdf.setFillColor(colors.HexColor("#23444b"))
    pdf.rect(0, height - 35 * mm, width, 35 * mm, stroke=0, fill=1)

    if logo_path.exists():
        pdf.drawImage(ImageReader(str(logo_path)), 15 * mm, height - 28 * mm, width=18 * mm, height=18 * mm, preserveAspectRatio=True, mask="auto")

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(38 * mm, height - 18 * mm, "Fosua Guesthouse - Aduman")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(38 * mm, height - 24 * mm, "Inventory POS Receipt")

    y = height - 45 * mm
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(18 * mm, y, f"Receipt #: {sale.receipt_number}")
    pdf.drawRightString(width - 18 * mm, y, f"{sale.created_at:%Y-%m-%d %H:%M}")

    y -= 8 * mm
    pdf.setFont("Helvetica", 10)
    pdf.drawString(18 * mm, y, f"Cashier: {sale.cashier.get_full_name() or sale.cashier.username}")
    y -= 6 * mm
    pdf.drawString(18 * mm, y, f"Customer: {sale.customer_name or '-'}")
    y -= 6 * mm
    pdf.drawString(18 * mm, y, f"Payment Method: {sale.get_payment_method_display()}")

    y -= 10 * mm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(18 * mm, y, "Items")
    y -= 5 * mm
    pdf.setFont("Helvetica", 9)
    for line in sale.items.select_related("item"):
        pdf.drawString(18 * mm, y, f"{line.item.name} x {line.quantity} @ GHS {line.unit_price}")
        pdf.drawRightString(width - 18 * mm, y, f"GHS {line.line_total}")
        y -= 5 * mm
        if y < 25 * mm:
            pdf.showPage()
            y = height - 20 * mm
            pdf.setFont("Helvetica", 9)

    y -= 4 * mm
    pdf.setStrokeColor(colors.HexColor("#d9d9d9"))
    pdf.line(18 * mm, y, width - 18 * mm, y)
    y -= 8 * mm
    pdf.setFont("Helvetica", 10)
    pdf.drawString(18 * mm, y, "Subtotal")
    pdf.drawRightString(width - 18 * mm, y, f"GHS {sale.subtotal}")
    y -= 6 * mm
    pdf.drawString(18 * mm, y, "Tax")
    pdf.drawRightString(width - 18 * mm, y, f"GHS {sale.tax_amount}")
    y -= 6 * mm
    pdf.drawString(18 * mm, y, "Discount")
    pdf.drawRightString(width - 18 * mm, y, f"GHS {sale.discount_amount}")
    y -= 6 * mm
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(18 * mm, y, "Grand Total")
    pdf.drawRightString(width - 18 * mm, y, f"GHS {sale.grand_total}")
    y -= 6 * mm
    pdf.setFont("Helvetica", 10)
    pdf.drawString(18 * mm, y, "Paid")
    pdf.drawRightString(width - 18 * mm, y, f"GHS {sale.amount_paid}")
    y -= 6 * mm
    pdf.drawString(18 * mm, y, "Change Due")
    pdf.drawRightString(width - 18 * mm, y, f"GHS {sale.change_due}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()
