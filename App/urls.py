from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, ReviewViewSet, RegisterView, LoginView, LogoutView, OrderViewSet
from django.urls import path

router = DefaultRouter()

router.register("products", ProductViewSet)
router.register("reviews", ReviewViewSet)
router.register("orders", OrderViewSet)

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("products/top-rated/", ProductViewSet.as_view({"get": "top_rated"})),
]


urlpatterns += router.urls