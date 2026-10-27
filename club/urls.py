from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("events", views.EventViewSet, basename="event")
router.register("projects", views.ProjectViewSet, basename="project")
router.register("team", views.TeamViewSet, basename="team")
router.register("library", views.LibraryViewSet, basename="library")
router.register("categories", views.CategoryViewSet, basename="category")
router.register("partners", views.PartnerViewSet, basename="partner")
router.register("project-categories", views.ProjectCategoryViewSet, basename="project-category")
router.register("technologies", views.TechnologyViewSet, basename="technology")

urlpatterns = [
    path("stats/", views.StatsView.as_view(), name="stats"),
    path("site/", views.SiteContentView.as_view(), name="site"),
    path("contact/", views.ContactCreateView.as_view(), name="contact"),
    path("registrations/", views.RegistrationCreateView.as_view(), name="registration-create"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/me/", views.MeView.as_view(), name="me"),
    path("analytics/track/", views.TrackView.as_view(), name="analytics-track"),
    path("analytics/summary/", views.AnalyticsSummaryView.as_view(), name="analytics-summary"),
    path("analytics/visits/", views.VisitListView.as_view(), name="analytics-visits"),
] + router.urls
