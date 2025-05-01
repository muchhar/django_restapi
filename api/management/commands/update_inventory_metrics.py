# api/management/commands/update_inventory_metrics.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.db.models import Sum, Q
from api.models import (
    User, Product, IncomingInventory, 
    UserInventory, Sales, DailyInventoryMetrics
)

class Command(BaseCommand):
    help = 'Updates inventory metrics and calculates projections'

    def handle(self, *args, **options):
        today = timezone.now().date()
        self.stdout.write(f"Processing inventory for {today}")
        
        # Process all users
        for user in User.objects.all():
            self.stdout.write(f"\nProcessing user: {user.username}")
            
            # 1. Process actual data for current date
            self.process_actual_day(user, today)
            
            # 2. Calculate projections for next 14 days
            for days_ahead in range(1, 15):
                future_date = today + timedelta(days=days_ahead)
                self.calculate_future_projections(user, future_date)

    def process_actual_day(self, user, date):
        """Process REAL sales/inventory for a specific date"""
        for product in Product.objects.all():
            # Get or create metrics record
            metrics, created = DailyInventoryMetrics.objects.get_or_create(
                user=user,
                product=product,
                date=date,
                defaults={'is_projection': False}
            )
            
            if not metrics.is_projection:
                # Update actual values
                metrics.sales = self.get_daily_sales(user, product, date)
                metrics.on_hand = self.get_current_inventory(user, product)
                metrics.incoming = self.get_incoming_inventory(user, product, date)
                metrics.lead_time_days = product.lead_time
                
                # Calculate derived metrics
                metrics.forecast = self.calculate_forecast(user, product, date)
                metrics.order_point = self.calculate_order_point(user, product, date, metrics.forecast)
                metrics.projected_on_hand = self.calculate_projected_on_hand(
                    user, product, date, metrics
                )
                metrics.soq = self.calculate_soq(metrics.projected_on_hand, metrics.order_point)
                metrics.planned_arrival = self.calculate_planned_arrival(
                    date, metrics.soq, product.lead_time
                )
                
                metrics.save()
                
                # Transfer arrived inventory
                self.transfer_arrived_inventory(user, product, date)

    def calculate_future_projections(self, user, future_date):
        """Calculate PROJECTED metrics for future dates"""
        for product in Product.objects.all():
            # Get previous day's data
            prev_date = future_date - timedelta(days=1)
            try:
                prev_metrics = DailyInventoryMetrics.objects.get(
                    user=user,
                    product=product,
                    date=prev_date
                )
            except DailyInventoryMetrics.DoesNotExist:
                continue
            
            # Calculate forecast (blend of actuals and projections)
            forecast = self.calculate_forecast(user, product, future_date)
            
            # Calculate other metrics
            order_point = self.calculate_order_point(user, product, future_date, forecast)
            projected_on_hand = self.calculate_projected_on_hand(
                user, product, future_date, prev_metrics
            )
            soq = self.calculate_soq(projected_on_hand, order_point)
            
            # Save as PROJECTION
            DailyInventoryMetrics.objects.update_or_create(
                user=user,
                product=product,
                date=future_date,
                is_projection=True,
                defaults={
                    'forecast': forecast,
                    'order_point': order_point,
                    'projected_on_hand': projected_on_hand,
                    'soq': soq,
                    'planned_arrival': self.calculate_planned_arrival(
                        future_date, soq, product.lead_time
                    ),
                    'lead_time_days': product.lead_time,
                    'incoming': self.get_incoming_inventory(user, product, future_date)
                }
            )

    # Helper Methods
    def get_daily_sales(self, user, product, date):
        """Sum all sales for a product on a given date"""
        return Sales.objects.filter(
            user=user,
            product=product,
            sale_date=date
        ).aggregate(total=Sum('quantity'))['total'] or Decimal(0)

    def get_current_inventory(self, user, product):
        """Get current on-hand inventory"""
        try:
            return UserInventory.objects.get(
                user=user,
                product=product
            ).quantity
        except UserInventory.DoesNotExist:
            return Decimal(0)

    def transfer_arrived_inventory(self, user, product, date):
        """Move arrived inventory to on-hand stock"""
        arrived_items = IncomingInventory.objects.filter(
            user=user,
            product=product,
            arrival_date__lte=date
        )
        
        total_arrived = sum(item.quantity for item in arrived_items)
        if total_arrived > 0:
            inventory, created = UserInventory.objects.get_or_create(
                user=user,
                product=product,
                defaults={'quantity': total_arrived}
            )
            if not created:
                inventory.quantity += total_arrived
                inventory.save()
            arrived_items.delete()

    def calculate_forecast(self, user, product, date):
        """7-day rolling average blending actuals and projections"""
        date_range = date - timedelta(days=7)
        
        # Get available data points
        data_points = []
        for single_date in (date - timedelta(days=n) for n in range(1, 8)):
            try:
                # Prefer actual sales data
                metrics = DailyInventoryMetrics.objects.get(
                    user=user,
                    product=product,
                    date=single_date,
                    is_projection=False
                )
                val = metrics.sales if metrics.sales else metrics.forecast
            except:
                try:
                    # Fall back to projections
                    metrics = DailyInventoryMetrics.objects.get(
                        user=user,
                        product=product,
                        date=single_date,
                        is_projection=True
                    )
                    val = metrics.forecast
                except:
                    val = Decimal(0)
            data_points.append(val)
        
        return sum(data_points) / 7 if data_points else Decimal(0)

    def calculate_order_point(self, user, product, date, forecast):
        """Sum of next lead_time_days forecasts"""
        lead_time = product.lead_time
        if lead_time == 0:
            return Decimal(0)
        
        total = forecast
        for i in range(1, lead_time):
            next_date = date + timedelta(days=i)
            try:
                metrics = DailyInventoryMetrics.objects.get(
                    user=user,
                    product=product,
                    date=next_date
                )
                total += metrics.forecast
            except DailyInventoryMetrics.DoesNotExist:
                total += forecast
        
        return total

    def calculate_projected_on_hand(self, user, product, date, prev_metrics):
        """Calculate projected on-hand inventory"""
        forecast = self.calculate_forecast(user, product, date)
        incoming = self.get_incoming_inventory(user, product, date)
        
        # Get planned arrivals (SOQ from lead_time days ago)
        planned_arrival = Decimal(0)
        if product.lead_time > 0:
            soq_date = date - timedelta(days=product.lead_time)
            try:
                soq_metrics = DailyInventoryMetrics.objects.get(
                    user=user,
                    product=product,
                    date=soq_date
                )
                planned_arrival = soq_metrics.soq
            except DailyInventoryMetrics.DoesNotExist:
                pass
        
        # Use actual on-hand if previous was a projection with zero
        starting_value = prev_metrics.on_hand if prev_metrics.projected_on_hand == 0 else prev_metrics.projected_on_hand
        
        projected = starting_value - forecast + incoming + planned_arrival
        return max(projected, Decimal(0))  # Can't go below zero

    def calculate_soq(self, projected_on_hand, order_point):
        """Calculate Suggested Order Quantity"""
        return max(order_point - projected_on_hand, Decimal(0))

    def calculate_planned_arrival(self, date, soq, lead_time):
        """Planned arrival is today's SOQ (will be applied in future)"""
        return soq

    def get_incoming_inventory(self, user, product, date):
        """Get incoming inventory for a specific date"""
        return IncomingInventory.objects.filter(
            user=user,
            product=product,
            arrival_date=date
        ).aggregate(total=Sum('quantity'))['total'] or Decimal(0)