import json
from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserAccessProfile
from inventory.models import (
    InventoryCategory,
    InventoryItem,
    InventorySubcategory,
    InventoryTransaction,
    Sale,
    Supplier,
)


class InventoryPermissionTests(TestCase):
    def setUp(self):
        self.admin_group = Group.objects.create(name="Admin")
        self.reception_group = Group.objects.create(name="Receptionist")
        self.admin = User.objects.create_user(username="inventory-admin", password="pass123456")
        self.admin.groups.add(self.admin_group)
        self.reception = User.objects.create_user(username="inventory-reception", password="pass123456")
        self.reception.groups.add(self.reception_group)
        UserAccessProfile.objects.create(
            user=self.reception,
            dashboard_access=True,
            reservations_access=True,
            rooms_access=True,
            guests_access=True,
            payments_access=True,
            services_access=True,
            housekeeping_access=True,
            inventory_access=False,
            pos_access=True,
            notifications_access=True,
            analytics_access=True,
            reports_access=False,
            settings_access=False,
            staff_management_access=False,
            handovers_access=True,
            users_roles_access=False,
        )

    def test_receptionist_cannot_open_inventory_dashboard(self):
        self.client.force_login(self.reception)
        response = self.client.get(reverse("inventory-dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_receptionist_can_open_pos_terminal(self):
        self.client.force_login(self.reception)
        response = self.client.get(reverse("inventory-pos"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fast checkout terminal")


class InventoryPosWorkflowTests(TestCase):
    def setUp(self):
        self.admin_group = Group.objects.create(name="Admin")
        self.user = User.objects.create_user(username="pos-admin", password="pass123456")
        self.user.groups.add(self.admin_group)

        self.category = InventoryCategory.objects.create(
            name="Soft Drinks",
            category_group=InventoryCategory.CategoryGroup.NON_ALCOHOLIC,
            description="Chilled drinks",
        )
        self.subcategory = InventorySubcategory.objects.create(
            category=self.category,
            name="Juices",
            description="Fruit juices",
        )
        self.supplier = Supplier.objects.create(name="Fresh Supply Co")
        self.item = InventoryItem.objects.create(
            name="Mango Juice",
            category=self.category,
            subcategory=self.subcategory,
            supplier=self.supplier,
            purchase_price="6.00",
            selling_price="10.00",
            quantity_in_stock="10.000",
            minimum_stock_threshold="2.000",
            unit_of_measure=InventoryItem.UnitOfMeasure.BOTTLE,
            description="Cold mango juice",
        )

    def test_item_creation_records_opening_stock_transaction(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("inventory-item-create"),
            {
                "name": "Coke Bottle",
                "category": self.category.pk,
                "subcategory": self.subcategory.pk,
                "supplier": self.supplier.pk,
                "purchase_price": "5.00",
                "selling_price": "8.00",
                "quantity_in_stock": "12.000",
                "unit_of_measure": InventoryItem.UnitOfMeasure.BOTTLE,
                "minimum_stock_threshold": "3.000",
                "description": "Chilled coke bottles",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        created_item = InventoryItem.objects.get(name="Coke Bottle")
        transactions = InventoryTransaction.objects.filter(
            item=created_item,
            transaction_type=InventoryTransaction.TransactionType.PURCHASE,
        )
        self.assertEqual(transactions.count(), 1)
        self.assertEqual(transactions.first().quantity_changed, created_item.quantity_in_stock)

    def test_pos_checkout_deducts_stock_and_creates_sale(self):
        self.client.force_login(self.user)
        cart = json.dumps([{"id": self.item.pk, "quantity": 3}])
        response = self.client.post(
            reverse("inventory-pos-checkout"),
            {
                "payment_method": Sale.PaymentMethod.CASH,
                "tax_amount": "0.00",
                "discount_amount": "0.00",
                "amount_paid": "30.00",
                "notes": "Bar sale",
                "cart": cart,
            },
        )
        self.assertEqual(response.status_code, 302)

        sale = Sale.objects.latest("created_at")
        self.item.refresh_from_db()
        self.assertEqual(sale.receipt_number.startswith("POS-"), True)
        self.assertEqual(str(sale.grand_total), "30.00")
        self.assertEqual(str(self.item.quantity_in_stock), "7.000")
        self.assertEqual(
            InventoryTransaction.objects.filter(
                item=self.item,
                sale=sale,
                transaction_type=InventoryTransaction.TransactionType.SALE,
            ).count(),
            1,
        )

    def test_sale_receipt_pdf_endpoint_returns_pdf(self):
        sale = Sale.objects.create(
            cashier=self.user,
            payment_method=Sale.PaymentMethod.CASH,
            subtotal="10.00",
            grand_total="10.00",
            amount_paid="10.00",
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("inventory-sale-pdf", args=[sale.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(sale.receipt_number, response["Content-Disposition"])

    def test_sale_list_csv_export_works(self):
        Sale.objects.create(
            cashier=self.user,
            payment_method=Sale.PaymentMethod.CASH,
            subtotal="10.00",
            grand_total="10.00",
            amount_paid="10.00",
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("inventory-sales"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("Receipt Number", response.content.decode())

    def test_inventory_dashboard_and_reports_render(self):
        self.client.force_login(self.user)
        dashboard = self.client.get(reverse("inventory-dashboard"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "Stock and POS overview")

        reports = self.client.get(reverse("inventory-reports"))
        self.assertEqual(reports.status_code, 200)
        self.assertContains(reports, "Sales and stock analytics")

    def test_quantity_fields_render_without_trailing_zeroes(self):
        self.client.force_login(self.user)

        item_form = self.client.get(reverse("inventory-item-update", args=[self.item.pk]))
        self.assertEqual(item_form.status_code, 200)
        self.assertContains(item_form, 'value="10"', html=False)
        self.assertContains(item_form, 'value="2"', html=False)
        self.assertNotContains(item_form, 'value="10.000"', html=False)
        self.assertNotContains(item_form, 'value="2.000"', html=False)

        adjustment_form = self.client.get(reverse("inventory-item-adjust", args=[self.item.pk]))
        self.assertEqual(adjustment_form.status_code, 200)
        self.assertContains(adjustment_form, "Adjust Mango Juice from 10")
        self.assertNotContains(adjustment_form, "Adjust Mango Juice from 10.000")

        item_list = self.client.get(reverse("inventory-items"))
        self.assertEqual(item_list.status_code, 200)
        self.assertContains(item_list, "Min 2")
        self.assertNotContains(item_list, "Min 2.000")
