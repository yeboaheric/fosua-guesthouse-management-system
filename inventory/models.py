from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from accounts.models import StatusTrackingMixin


class InventoryCategory(models.Model):
    class CategoryGroup(models.TextChoices):
        NON_ALCOHOLIC = "non_alcoholic", "Non-alcoholic beverages"
        ALCOHOLIC = "alcoholic", "Alcoholic beverages"
        FOODSTUFF = "foodstuff", "Foodstuff"

    name = models.CharField(max_length=120, unique=True)
    category_group = models.CharField(max_length=20, choices=CategoryGroup.choices)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category_group", "name"]

    def __str__(self):
        return self.name


class InventorySubcategory(models.Model):
    category = models.ForeignKey(
        InventoryCategory,
        on_delete=models.CASCADE,
        related_name="subcategories",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["category", "name"], name="unique_inventory_subcategory_per_category"),
        ]

    def __str__(self):
        return f"{self.category.name} / {self.name}"


class Supplier(models.Model):
    name = models.CharField(max_length=160, unique=True)
    contact_person = models.CharField(max_length=160, blank=True)
    phone_number = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class InventoryItem(StatusTrackingMixin, models.Model):
    class InventoryStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        LOW_STOCK = "low_stock", "Low Stock"
        OUT_OF_STOCK = "out_of_stock", "Out of Stock"
        DISCONTINUED = "discontinued", "Discontinued"

    class UnitOfMeasure(models.TextChoices):
        PIECE = "piece", "Piece"
        BOTTLE = "bottle", "Bottle"
        CAN = "can", "Can"
        PACK = "pack", "Pack"
        CARTON = "carton", "Carton"
        KILOGRAM = "kg", "Kilogram"
        GRAM = "g", "Gram"
        LITRE = "l", "Litre"
        MILLILITRE = "ml", "Millilitre"
        BAG = "bag", "Bag"

    name = models.CharField(max_length=160)
    category = models.ForeignKey(
        InventoryCategory,
        on_delete=models.PROTECT,
        related_name="items",
    )
    subcategory = models.ForeignKey(
        InventorySubcategory,
        on_delete=models.PROTECT,
        related_name="items",
        blank=True,
        null=True,
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        related_name="items",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=InventoryStatus.choices,
        default=InventoryStatus.ACTIVE,
        blank=True,
    )
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity_in_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    unit_of_measure = models.CharField(max_length=20, choices=UnitOfMeasure.choices, default=UnitOfMeasure.PIECE)
    minimum_stock_threshold = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="inventory_items/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    date_added = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__name", "subcategory__name", "name"]
        indexes = [
            models.Index(fields=["quantity_in_stock"]),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.quantity_in_stock is not None and self.quantity_in_stock < 0:
            raise ValidationError("Quantity in stock cannot be negative.")
        if self.minimum_stock_threshold is not None and self.minimum_stock_threshold < 0:
            raise ValidationError("Minimum stock threshold cannot be negative.")
        if self.subcategory and self.subcategory.category_id != self.category_id:
            raise ValidationError("The selected subcategory does not belong to the selected category.")

    def save(self, *args, **kwargs):
        if self.status != self.InventoryStatus.DISCONTINUED:
            quantity = None
            minimum_threshold = None
            try:
                quantity = Decimal(self.quantity_in_stock)
            except (TypeError, ValueError, InvalidOperation):
                quantity = None
            try:
                minimum_threshold = Decimal(self.minimum_stock_threshold)
            except (TypeError, ValueError, InvalidOperation):
                minimum_threshold = None

            if quantity is not None and quantity <= 0:
                self.status = self.InventoryStatus.OUT_OF_STOCK
            elif quantity is not None and minimum_threshold is not None and quantity <= minimum_threshold:
                self.status = self.InventoryStatus.LOW_STOCK
            else:
                self.status = self.InventoryStatus.ACTIVE
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def stock_value(self):
        return Decimal(self.purchase_price) * Decimal(self.quantity_in_stock)

    @property
    def is_low_stock(self):
        return self.quantity_in_stock <= self.minimum_stock_threshold


class InventoryTransaction(models.Model):
    class TransactionType(models.TextChoices):
        PURCHASE = "purchase", "Purchase"
        SALE = "sale", "Sale"
        ADJUSTMENT = "adjustment", "Adjustment"
        DAMAGE = "damage", "Damage"
        USAGE = "usage", "Operational Use"
        TRANSFER_IN = "transfer_in", "Transfer In"
        TRANSFER_OUT = "transfer_out", "Transfer Out"

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    sale = models.ForeignKey(
        "Sale",
        on_delete=models.SET_NULL,
        related_name="transactions",
        blank=True,
        null=True,
    )
    stock_adjustment = models.ForeignKey(
        "StockAdjustment",
        on_delete=models.SET_NULL,
        related_name="transactions",
        blank=True,
        null=True,
    )
    quantity_before = models.DecimalField(max_digits=12, decimal_places=3)
    quantity_changed = models.DecimalField(max_digits=12, decimal_places=3)
    quantity_after = models.DecimalField(max_digits=12, decimal_places=3)
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="inventory_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["transaction_type", "created_at"])]

    def __str__(self):
        return f"{self.get_transaction_type_display()} for {self.item.name}"


class StockAdjustment(models.Model):
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="adjustments",
    )
    previous_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    new_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    reason = models.CharField(max_length=120)
    notes = models.TextField(blank=True)
    adjusted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="stock_adjustments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Adjustment for {self.item.name}"


class Sale(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        MIXED = "mixed", "Mixed"

    class SaleStatus(models.TextChoices):
        COMPLETED = "completed", "Completed"
        VOID = "void", "Void"

    receipt_number = models.CharField(max_length=40, unique=True, blank=True)
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sales",
    )
    customer_name = models.CharField(max_length=160, blank=True)
    customer_phone = models.CharField(max_length=40, blank=True)
    customer_email = models.EmailField(blank=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    change_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=SaleStatus.choices, default=SaleStatus.COMPLETED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["receipt_number", "created_at"])]

    def __str__(self):
        return self.receipt_number or f"Sale #{self.pk}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = self.generate_receipt_number()
        amount_paid = Decimal(str(self.amount_paid or 0))
        grand_total = Decimal(str(self.grand_total or 0))
        if amount_paid or grand_total:
            self.amount_paid = amount_paid
            self.grand_total = grand_total
            self.change_due = max(amount_paid - grand_total, Decimal("0.00"))
        super().save(*args, **kwargs)

    @staticmethod
    def generate_receipt_number():
        stamp = timezone.now().strftime("%Y%m%d")
        token = uuid4().hex[:6].upper()
        return f"POS-{stamp}-{token}"

    @property
    def total_items(self):
        return self.items.aggregate(total=Sum("quantity"))["total"] or Decimal("0")


class SaleItem(models.Model):
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="items",
    )
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="sale_items",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.item.name} x {self.quantity}"
