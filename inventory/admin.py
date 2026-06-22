from django.contrib import admin

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


@admin.register(InventoryCategory)
class InventoryCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category_group", "created_at")
    search_fields = ("name", "description")
    list_filter = ("category_group",)


@admin.register(InventorySubcategory)
class InventorySubcategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "created_at")
    search_fields = ("name", "category__name")
    list_filter = ("category",)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_person", "phone_number", "is_active")
    search_fields = ("name", "contact_person", "phone_number")
    list_filter = ("is_active",)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "quantity_in_stock", "unit_of_measure", "is_active")
    search_fields = ("name", "category__name", "subcategory__name", "supplier__name")
    list_filter = ("category", "subcategory", "supplier", "unit_of_measure", "is_active")


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ("item", "transaction_type", "quantity_changed", "quantity_after", "created_at")
    search_fields = ("item__name", "reference", "notes", "created_by__username")
    list_filter = ("transaction_type", "created_at")


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ("item", "quantity", "unit_price", "line_total")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "cashier", "payment_method", "grand_total", "edited_at", "created_at")
    search_fields = ("receipt_number", "customer_name", "customer_phone", "customer_email")
    list_filter = ("payment_method", "status", "edited_at", "created_at")
    inlines = [SaleItemInline]


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("item", "reason", "adjusted_by", "created_at")
    search_fields = ("item__name", "reason", "adjusted_by__username")
    list_filter = ("created_at",)
