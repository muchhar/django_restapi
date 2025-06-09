from django.db import models
from django.contrib.auth.models import AbstractUser


class ImageUpload(models.Model):
    image = models.ImageField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image uploaded at {self.uploaded_at}"
class User(AbstractUser):
    is_admin = models.BooleanField(default=False)
    
    # Avoid reverse accessor clashes
    groups = models.ManyToManyField(
        'auth.Group',
        related_name="api_user_groups",
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name="api_user_permissions",
        blank=True,
    )

    def __str__(self):
        return self.username
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class Product(models.Model):
    product_number = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    lead_time = models.PositiveIntegerField(default=0)  # in days
    
    def __str__(self):
        return f"{self.product_number} - {self.name}"

class OldUserInventory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    date = models.DateField()  
    class Meta:
        unique_together = ('user', 'product','date')
    
    def __str__(self):
        return f"{self.user.username}'s {self.product.name}: {self.quantity} {self.date}"

class UserInventory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ('user', 'product')
    
    def __str__(self):
        return f"{self.user.username}'s {self.product.name}: {self.quantity}"
class OldIncomingInventory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    arrival_date = models.DateField()  # Calculated as order_date + lead_time
    
    class Meta:
        unique_together = ('user', 'product', 'arrival_date')
    
    def __str__(self):
        return f"{self.product.name} arriving on {self.arrival_date}"

class IncomingInventory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    arrival_date = models.DateField()  # Calculated as order_date + lead_time
    
    class Meta:
        unique_together = ('user', 'product', 'arrival_date')
    
    def __str__(self):
        return f"{self.product.name} arriving on {self.arrival_date}"

class Sales(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    sale_date = models.DateField(auto_now_add=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} sold {self.quantity} {self.product.name}"
    
class DailyInventoryMetrics(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    date = models.DateField()
    is_projection = models.BooleanField(default=False)
    
    # Core metrics
    sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    on_hand = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    incoming = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Calculated metrics
    order_point = models.DecimalField(max_digits=10, decimal_places=2)
    lead_time_days = models.PositiveIntegerField()
    forecast = models.DecimalField(max_digits=10, decimal_places=2)
    projected_on_hand = models.DecimalField(max_digits=10, decimal_places=2)
    soq = models.DecimalField(max_digits=10, decimal_places=2)
    planned_arrival = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('user', 'product', 'date', 'is_projection')
        ordering = ['-date']

    def __str__(self):
        type_flag = "PROJ" if self.is_projection else "ACTUAL"
        return f"{type_flag} {self.user.username}'s {self.product.name} metrics for {self.date}"