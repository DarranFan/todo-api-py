from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, TaskViewSet


router = DefaultRouter()
router.register("categories", CategoryViewSet)
router.register("tasks", TaskViewSet)

urlpatterns = router.urls
