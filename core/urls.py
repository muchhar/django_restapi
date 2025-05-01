from django.contrib import admin
from django.urls import path, include
from api.views import (
    RegisterView, LoginView, UserProfileView,
    CategoryListCreateView, CategoryDetailView,
    ProductListCreateView, ProductDetailView,
    SalesListCreateView, SalesDetailView,
    IncomingInventoryListCreateView, IncomingInventoryDetailView,
    BuyProductSerializer,SellProductSerializer,
    BuyProductView,SellProductView,
    MetricsView,ProcessProductImageView,ImageTextExtractView
)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/profile/', UserProfileView.as_view(), name='profile'),
    
    # Categories
    path('api/categories/', CategoryListCreateView.as_view(), name='category-list'),
    path('api/categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    
    # Products
    path('api/products/', ProductListCreateView.as_view(), name='product-list'),
    path('api/products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    
    # Inventory
    
    # Sales
    path('api/buy/', BuyProductView.as_view(), name='buy-product'),
    path('api/sell/', SellProductView.as_view(), name='sell-product'),
    path('api/sales/', SalesListCreateView.as_view(), name='sales-list'),
    path('api/sales/<int:pk>/', SalesDetailView.as_view(), name='sales-detail'),
    
    # Incoming Inventory
    path('api/incoming/', IncomingInventoryListCreateView.as_view(), name='incoming-list'),
    path('api/incoming/<int:pk>/', IncomingInventoryDetailView.as_view(), name='incoming-detail'),
    
    
    # Metrics
    path('api/metrics/<int:product_id>/', MetricsView.as_view(), name='metrics'),
    path('api/process-image/', ProcessProductImageView.as_view(), name='process-image'),

    #img
    path('api/extract-text/', ImageTextExtractView.as_view(), name='extract-text'),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)