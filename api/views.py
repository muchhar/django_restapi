from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from api.models import User
from .models import Category, Product, Sales, IncomingInventory
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .serializers import (
    UserSerializer, MyTokenObtainPairSerializer, 
    CategorySerializer, ProductSerializer,
     SalesSerializer,
    IncomingInventorySerializer,
    BuyProductSerializer,SellProductSerializer,UserInventory
)
from google.cloud import vision
from .serializers import ImageProcessingSerializer
import os
import base64
from django.conf import settings
from rest_framework.parsers import MultiPartParser
from .serializers import ImageUploadSerializer

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(settings.BASE_DIR, 'service_account.json')
class ImageTextExtractView(APIView):
    parser_classes = (MultiPartParser,)
    
    def post(self, request, format=None):
        serializer = ImageUploadSerializer(data=request.data)
        if serializer.is_valid():
            image_instance = serializer.save()
            image_path = os.path.join(settings.MEDIA_ROOT, str(image_instance.image))
            
            # Initialize Google Vision client
            client = vision.ImageAnnotatorClient()
            
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = client.text_detection(image=image)
            texts = response.text_annotations
            
            if response.error.message:
                return Response(
                    {'error': response.error.message},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            extracted_text = texts[0].description if texts else "No text found"
            
            return Response({
                'image_id': image_instance.id,
                'extracted_text': extracted_text
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class ProcessProductImageView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ImageProcessingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
       
        try:
            client = vision.ImageAnnotatorClient()
            image_base64 = serializer.validated_data['image']
            image_content = base64.b64decode(image_base64)
            image = vision.Image(content=image_content)
            
            # Use document_text_detection instead of text_detection for better results
            response = client.document_text_detection(
                image=image,
                image_context=vision.ImageContext(
                    language_hints=["en"],
                    text_detection_params=vision.TextDetectionParams(
                        enable_text_detection_confidence_score=True
                    )
                )
            )
            
            if response.error.message:
                return Response(
                    {'error': response.error.message},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process text blocks with their positions
            detected_texts = []
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            word_text = ''.join([symbol.text for symbol in word.symbols])
                            detected_texts.append({
                                'text': word_text,
                                'confidence': word.confidence,
                                'bounds': [(vertex.x, vertex.y) for vertex in word.bounding_box.vertices]
                            })
            
            # Sort text by reading order (top to bottom, left to right)
            detected_texts.sort(key=lambda x: (x['bounds'][0][1], x['bounds'][0][0]))
            
            # Extract all text in order
            ordered_text = [item['text'] for item in detected_texts]
            
            return Response({
                'success': True,
                'texts': ordered_text,
                'full_response': detected_texts  # For debugging
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

class LoginView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class BuyProductView(generics.CreateAPIView):
    serializer_class = BuyProductSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']
        user = request.user
        
        # Calculate arrival date
        arrival_date = timezone.now().date() + timezone.timedelta(days=product.lead_time)
        
        # Create incoming inventory record
        IncomingInventory.objects.create(
            user=user,
            product=product,
            quantity=quantity,
            arrival_date=arrival_date
        )
        
        return Response(
            {"message": f"{quantity} {product.name} will arrive on {arrival_date}"},
            status=status.HTTP_201_CREATED
        )

class SellProductView(generics.CreateAPIView):
    serializer_class = SellProductSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']
        user = request.user
        
        # Get user's inventory
        try:
            inventory = UserInventory.objects.get(user=user, product=product)
        except UserInventory.DoesNotExist:
            raise ValidationError("You don't have any of this product in stock")
        
        # Check available quantity
        if inventory.quantity < quantity:
            raise ValidationError(
                f"Only {inventory.quantity} available, but requested {quantity}"
            )
        
        # Update inventory
        inventory.quantity -= quantity
        inventory.save()
        
        # Record sale
        Sales.objects.create(
            user=user,
            product=product,
            quantity=quantity
        )
        
        return Response(
            {"message": f"Successfully sold {quantity} {product.name}"},
            status=status.HTTP_201_CREATED
        )
class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]



# class SalesListCreateView(generics.ListCreateAPIView):
#     queryset = Sales.objects.all()
#     serializer_class = SalesSerializer
#    permission_classes = [permissions.IsAuthenticated]
class SalesListCreateView(generics.ListCreateAPIView):
    serializer_class = SalesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return only the current user's sales"""
        return Sales.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Automatically assign the current user to new sales"""
        serializer.save(user=self.request.user)
class SalesDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Sales.objects.all()
    serializer_class = SalesSerializer
    permission_classes = [permissions.IsAuthenticated]

class IncomingInventoryListCreateView(generics.ListCreateAPIView):
    queryset = IncomingInventory.objects.all()
    serializer_class = IncomingInventorySerializer
    permission_classes = [permissions.IsAuthenticated]

class IncomingInventoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = IncomingInventory.objects.all()
    serializer_class = IncomingInventorySerializer
    permission_classes = [permissions.IsAuthenticated]



class MetricsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, product_id):
        # Implement your metrics calculation logic here
        # This should return all 9 metrics as shown in the Excel example
        # You'll need to implement the complex calculations for:
        # - Forecast (7-day rolling average)
        # - Order Point (sum of forecast based on lead time)
        # - Projected On-Hand
        # - SOQ (Suggested Order Quantity)
        # - Planned Arrival
        
        # Placeholder response - you'll need to implement the actual calculations
        return Response({
            "product_id": product_id,
            "metrics": {
                "sales": [],
                "on_hand": [],
                "incoming": [],
                "order_point": [],
                "lead_time": 0,
                "forecast": [],
                "projected_on_hand": [],
                "soq": [],
                "planned_arrival": []
            }
        })