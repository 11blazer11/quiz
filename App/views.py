from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import SAFE_METHODS, IsAuthenticatedOrReadOnly, IsAuthenticated
from .models import Order, Product, Review
from .serializers import ProductSerializer, ReviewSerializer, LoginSerializer, RegisterSerializer, OrderSerializer
from rest_framework.views import APIView, PermissionDenied
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .tasks import send_order_email, update_product_stock, daily_statistics
from django.core.cache import cache
from django.contrib.auth import authenticate
from rest_framework import mixins, generics
from rest_framework.decorators import action
from .permissions import (
    IsSeller,
    IsSellerOrReadOnly,
    IsReviewOwnerOrReadOnly,
)
from .tasks import (
    send_order_email,
    update_product_stock,
    daily_statistics
)

def generate_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def perform_create(self, serializer):
        user = self.request.user

        if not user.is_authenticated:
            raise PermissionDenied("Authentication required")
    
        serializer.save(customer=user)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role
            }
        }, status=status.HTTP_200_OK)


class LogoutView(mixins.DestroyModelMixin, generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({"message": "Logged out"})

        except Exception:
            return Response(
                {"error": "Invalid token"},
                status=400
            )
        
#crud operaciebi
class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # permission_classes = [IsSellerOrReadOnly]

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def review(self, request, pk=None):
        product = self.get_object()

        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save(user=request.user, product=product)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):

        product = serializer.save(
            seller=self.request.user
        )

        update_product_stock.delay(product.id)

    def perform_update(self, serializer):

        product = serializer.save()

        update_product_stock.delay(product.id)


    def get_serialized_products(self):
        cache_key = "products_list"
        cached_data = cache.get(cache_key)

        if cached_data:
            return cached_data

        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        cache.set(cache_key, serializer.data, timeout=60 * 5)

        return serializer.data


    def list(self, request, *args, **kwargs):
        import time
        start = time.time()  
        data = self.get_serialized_products()
        end = time.time()
        print(f"Time taken: {end - start} seconds")
        return Response(data)
    
    def get_top_rated_products(self):
        cache_key = "top_rated_products"
        cached_data = cache.get(cache_key)

        if cached_data:
            return cached_data

        products = list(Product.objects.all())

        products.sort(
            key=lambda product: sum(
                review.rating
                for review in product.reviews.all()
            ),
            reverse=True
        )

        serializer = self.get_serializer(products[:5], many=True)

        cache.set(cache_key, serializer.data, timeout=60 * 5)

        return serializer.data

    @action(detail=False, methods=["get"], url_path="top-products")
    def top_products(self, request):
        import time
        start = time.time()

        data = self.get_top_rated_products()

        end = time.time()
        print(f"Time taken: {end - start} seconds")

        return Response(data)


class OrderViewSet(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):

        order = serializer.save(customer=self.request.user)

        send_order_email.delay(self.request.user.email, order.id)

        daily_statistics.delay()


class ReviewViewSet(ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

    def get_permissions(self):

        if self.action == "create":
            return [IsAuthenticated()]

        return [IsAuthenticatedOrReadOnly(),
                IsReviewOwnerOrReadOnly()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)