from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Category, Product, UserInventory, Sales, IncomingInventory
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import base64

User = get_user_model()  # Ensures we use the custom User model
from .models import ImageUpload

class ImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageUpload
        fields = ('id', 'image', 'uploaded_at')
        read_only_fields = ('uploaded_at',)
class ImageProcessingSerializer(serializers.Serializer):
    image = serializers.CharField()
    product_id = serializers.IntegerField(required=False)
    
    def validate_image(self, value):
        try:
            # Validate it's a proper base64 image
            if ',' in value:
                value = value.split(',')[1]
            base64.b64decode(value)
            return value
        except:
            raise serializers.ValidationError("Invalid base64 image data")

class BuyProductSerializer(serializers.Serializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product'
    )
    quantity = serializers.IntegerField(min_value=1)

class SellProductSerializer(serializers.Serializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product'
    )
    quantity = serializers.IntegerField(min_value=1)
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'is_admin']
        extra_kwargs = {'password': {'write_only': True}}
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            is_admin=validated_data.get('is_admin', False)
        )
        return user
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['username'] = user.username
        token['is_admin'] = user.is_admin
        
        return token

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), 
        source='category', 
        write_only=True
    )
    
    class Meta:
        model = Product
        fields = '__all__'

class InventorySerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), 
        source='product', 
        write_only=True
    )
    
    class Meta:
        model = UserInventory
        fields = '__all__'

class SalesSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), 
        source='product', 
        write_only=True
    )
    
    class Meta:
        model = Sales
        fields = '__all__'

class IncomingInventorySerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), 
        source='product', 
        write_only=True
    )
    
    class Meta:
        model = IncomingInventory
        fields = '__all__'

