from datetime import timedelta

from django.db.models import Count, F, Prefetch, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from .icons import PROJECT_SUMMARY_ICONS, STAT_ICONS, icon_payload
from .models import (
    Category, ClubSettings, ContentBlock, Event, MediaItem, Partner, Project, ProjectCategory,
    Registration, TeamMember, Technology, Visit,
)
from .serializers import (
    CategorySerializer, ContactMessageSerializer, ContentBlockSerializer, EventSerializer,
    MediaItemSerializer, MeSerializer, PartnerSerializer, ProjectCategoryCountSerializer,
    ProjectSerializer, RegistrationSerializer, TeamMemberSerializer, TechnologyUsageSerializer,
    TrackSerializer, VisitSerializer,
)
from .utils import client_ip, estimate, geolocate, mask_ip, parse_user_agent


def get_limit(request, default=None, maximum=100):
    """?limit=N  (entier >= 1). Sans paramètre : `default` (None = tout renvoyer)."""
    raw = request.query_params.get("limit")
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValidationError({"limit": "Doit être un entier."})
    if value < 1:
        raise ValidationError({"limit": "Doit être supérieur ou égal à 1."})
    return min(value, maximum)


def upcoming_q(now):
    """À venir = commence plus tard, ou date encore « à confirmer » (starts_at vide)."""
    return Q(starts_at__gt=now) | Q(starts_at__isnull=True)


def soonest_first(qs):
    return qs.order_by(F("starts_at").asc(nulls_last=True), "id")


def limited(qs, limit):
    return qs[:limit] if limit else qs


# ---------------------------------------------------------------------------
# Catégories
# ---------------------------------------------------------------------------
class CategoryViewSet(ReadOnlyModelViewSet):
    """GET /api/categories/"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = None


# ---------------------------------------------------------------------------
# Évènements
# ---------------------------------------------------------------------------
class EventViewSet(ReadOnlyModelViewSet):
    """
    GET /api/events/                     liste (filtres : ?kind= ?category=<slug> ?status=upcoming|ongoing|finished|to_be_confirmed)
    GET /api/events/recent/?limit=N      derniers évènements déjà commencés/terminés
    GET /api/events/upcoming/?limit=N    évènements à venir
    GET /api/events/overview/            à venir, ateliers, formations, compétitions
    GET /api/events/by-category/         évènements regroupés par catégorie
    """

    serializer_class = EventSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Event.objects.prefetch_related("categories")
            .annotate(taken=Count("registrations", filter=~Q(registrations__status=Registration.Status.CANCELLED)))
            .order_by(F("starts_at").desc(nulls_last=True), "-id")
        )

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        p = request.query_params
        if p.get("kind"):
            qs = qs.filter(kind=p["kind"])
        if p.get("category"):
            qs = qs.filter(categories__slug=p["category"])
        now = timezone.now()
        st = p.get("status")
        if st == "upcoming":
            qs = soonest_first(qs.filter(upcoming_q(now)))
        elif st == "to_be_confirmed":
            qs = qs.filter(starts_at__isnull=True)
        elif st == "ongoing":
            qs = qs.filter(starts_at__lte=now, ends_at__gte=now)
        elif st == "finished":
            qs = qs.filter(ends_at__lt=now)
        return Response(self.get_serializer(limited(qs, get_limit(request)), many=True).data)

    @action(detail=False, methods=["get"])
    def recent(self, request):
        qs = self.get_queryset().filter(starts_at__lte=timezone.now()).order_by("-starts_at")
        if request.query_params.get("kind"):
            qs = qs.filter(kind=request.query_params["kind"])
        return Response(self.get_serializer(limited(qs, get_limit(request)), many=True).data)

    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        qs = soonest_first(self.get_queryset().filter(upcoming_q(timezone.now())))
        if request.query_params.get("kind"):
            qs = qs.filter(kind=request.query_params["kind"])
        return Response(self.get_serializer(limited(qs, get_limit(request)), many=True).data)

    @action(detail=False, methods=["get"])
    def overview(self, request):
        """?limit=N (défaut 10 par liste) &recent_days=N (défaut 60 : fenêtre « réalisés récemment »)."""
        limit = get_limit(request, default=10)
        try:
            recent_days = int(request.query_params.get("recent_days", 60))
        except ValueError:
            raise ValidationError({"recent_days": "Doit être un entier."})
        now = timezone.now()
        since = now - timedelta(days=recent_days)
        base = self.get_queryset()

        def upcoming(kind):
            return soonest_first(base.filter(upcoming_q(now), kind=kind))

        def ongoing(kind):
            return base.filter(kind=kind, starts_at__lte=now, ends_at__gte=now).order_by("ends_at")

        def done(kind, only_recent=False):
            qs = base.filter(kind=kind, ends_at__lt=now)
            if only_recent:
                qs = qs.filter(ends_at__gte=since)
            return qs.order_by("-ends_at")

        def ser(qs):
            return self.get_serializer(limited(qs, limit), many=True).data

        K = Event.Kind
        return Response({
            "upcoming_events": ser(upcoming(K.EVENT)),
            "workshops": {
                "upcoming": ser(upcoming(K.WORKSHOP)),
                "ongoing": ser(ongoing(K.WORKSHOP)),
                "recently_completed": ser(done(K.WORKSHOP, only_recent=True)),
            },
            "trainings": {
                "upcoming": ser(upcoming(K.TRAINING)),
                "ongoing": ser(ongoing(K.TRAINING)),
                "completed": ser(done(K.TRAINING)),
            },
            "competitions": {
                "upcoming": ser(upcoming(K.COMPETITION)),
                "ongoing": ser(ongoing(K.COMPETITION)),
                "completed": ser(done(K.COMPETITION)),
            },
        })

    @action(detail=False, methods=["get"], url_path="by-category")
    def by_category(self, request):
        """?kind= pour restreindre à un type ; ?limit=N par catégorie."""
        events = self.get_queryset()
        if request.query_params.get("kind"):
            events = events.filter(kind=request.query_params["kind"])
        limit = get_limit(request)
        categories = Category.objects.prefetch_related(Prefetch("events", queryset=events, to_attr="listed_events"))
        data = []
        for cat in categories:
            items = cat.listed_events[:limit] if limit else cat.listed_events
            if not items:
                continue
            data.append({
                "category": CategorySerializer(cat).data,
                "count": len(cat.listed_events),
                "events": self.get_serializer(items, many=True).data,
            })
        return Response(data)


# ---------------------------------------------------------------------------
# Projets
# ---------------------------------------------------------------------------
class ProjectViewSet(ReadOnlyModelViewSet):
    """
    GET /api/projects/                 liste (filtres : ?category=<slug> ?search=texte ?technology=<nom> ?limit=)
    GET /api/projects/recent/?limit=N  N projets les plus récents (sans limit : tous)
    GET /api/projects/summary/         « En chiffres » de la page Projets
    GET /api/projects/<id>/
    """

    serializer_class = ProjectSerializer
    pagination_class = None
    queryset = Project.objects.select_related("category").prefetch_related("technologies", "members__user")

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        p = request.query_params
        if p.get("category"):
            qs = qs.filter(category__slug=p["category"])
        if p.get("technology"):
            qs = qs.filter(technologies__name__iexact=p["technology"])
        if p.get("search"):
            term = p["search"].strip()
            qs = qs.filter(
                Q(title__icontains=term) | Q(description__icontains=term) | Q(technologies__name__icontains=term)
                | Q(category__name__icontains=term)
            )
        qs = qs.distinct().order_by("-date", "-id")
        return Response(self.get_serializer(limited(qs, get_limit(request)), many=True).data)

    @action(detail=False, methods=["get"])
    def recent(self, request):
        qs = self.get_queryset().order_by("-date", "-id")
        return Response(self.get_serializer(limited(qs, get_limit(request)), many=True).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        projects = list(self.get_queryset())
        technologies = Technology.objects.filter(project__isnull=False).distinct().count()
        icons = PROJECT_SUMMARY_ICONS

        def item(key, title, value):
            return {"title": title, "value": value, "icon": icon_payload(icons[key])}

        return Response({
            "projects": item("projects", "projets présentés", len(projects)),
            "categories": item("categories", "catégories", ProjectCategory.objects.count()),
            "team_participations": item(
                "team_participations", "participations d'équipe", sum(pr.team_count for pr in projects)
            ),
            "technologies": item("technologies", "technologies citées", technologies),
        })


class ProjectCategoryViewSet(ReadOnlyModelViewSet):
    """GET /api/project-categories/  -> onglets de filtre de la page Projets (avec icône et nombre de projets)"""

    serializer_class = ProjectCategoryCountSerializer
    pagination_class = None
    queryset = ProjectCategory.objects.annotate(project_count=Count("projects"))


class TechnologyViewSet(ReadOnlyModelViewSet):
    """GET /api/technologies/  -> technologies utilisées par au moins un projet"""

    serializer_class = TechnologyUsageSerializer
    pagination_class = None
    queryset = Technology.objects.annotate(project_count=Count("project")).filter(project_count__gt=0)


# ---------------------------------------------------------------------------
# Équipe, bibliothèque, partenaires
# ---------------------------------------------------------------------------
class TeamViewSet(ReadOnlyModelViewSet):
    """GET /api/team/"""

    serializer_class = TeamMemberSerializer
    pagination_class = None
    queryset = TeamMember.objects.filter(is_public=True).select_related("user")


class LibraryPagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 100


class LibraryViewSet(ReadOnlyModelViewSet):
    """GET /api/library/?type=image|video&page=1&page_size=24"""

    serializer_class = MediaItemSerializer
    pagination_class = LibraryPagination

    def get_queryset(self):
        qs = MediaItem.objects.all()
        media_type = self.request.query_params.get("type")
        if media_type in ("image", "video"):
            qs = qs.filter(media_type=media_type)
        return qs


class PartnerViewSet(ReadOnlyModelViewSet):
    """GET /api/partners/"""

    serializer_class = PartnerSerializer
    pagination_class = None
    queryset = Partner.objects.filter(is_active=True)


# ---------------------------------------------------------------------------
# Statistiques (estimations)
# ---------------------------------------------------------------------------
class StatsView(APIView):
    """GET /api/stats/  ->  {"active_members": {"display": "150+", "value": 150, ...}, ...}"""

    permission_classes = [AllowAny]

    def get(self, request):
        members = ClubSettings.load().active_members or TeamMember.objects.filter(is_public=True).count()
        projects = Project.objects.filter(status=Project.Status.COMPLETED).count()
        years = Event.objects.dates("date", "year").count()
        per_year = round(Event.objects.count() / years) if years else 0
        partners = Partner.objects.filter(is_active=True).count()

        def stat(key, title, n):
            return {"title": title, **estimate(n), "icon": icon_payload(STAT_ICONS[key])}

        return Response({
            "active_members": stat("active_members", "Membres actifs", members),
            "completed_projects": stat("completed_projects", "Projets réalisés", projects),
            "events_per_year": stat("events_per_year", "Évènements par an", per_year),
            "partners": stat("partners", "Partenaires", partners),
        })


# ---------------------------------------------------------------------------
# Contenu éditorial du site + contact
# ---------------------------------------------------------------------------
class SiteContentView(APIView):
    """GET /api/site/  ->  textes « À propos », mission, valeurs, « Pourquoi participer ? », atouts, coordonnées"""

    permission_classes = [AllowAny]

    def get(self, request):
        cfg = ClubSettings.load()
        blocks = ContentBlock.objects.filter(is_active=True)

        def section(name):
            return ContentBlockSerializer(blocks.filter(section=name), many=True).data

        S = ContentBlock.Section
        return Response({
            "about": cfg.about_text,
            "mission": cfg.mission,
            "values": section(S.VALUE),
            "why_participate": section(S.WHY),
            "perks": section(S.PERK),
            "contact": {"email": cfg.contact_email, "phone": cfg.contact_phone, "address": cfg.address},
        })


class ContactCreateView(generics.CreateAPIView):
    """POST /api/contact/ {name, email, subject?, message}  (bouton « Nous contacter »)"""

    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "contact"


# ---------------------------------------------------------------------------
# Inscriptions
# ---------------------------------------------------------------------------
class RegistrationCreateView(generics.CreateAPIView):
    """POST /api/registrations/  {event|project|rien, full_name, email, phone?, message?}"""

    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "registrations"


# ---------------------------------------------------------------------------
# Connexion des membres
# ---------------------------------------------------------------------------
class LoginView(ObtainAuthToken):
    """POST /api/auth/login/ {username, password} -> {token, member}"""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        profile = getattr(user, "team_profile", None)
        return Response({
            "token": token.key,
            "member": MeSerializer(profile, context={"request": request}).data if profile else None,
        })


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/me/  (en-tête  Authorization: Token <token>)"""

    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile = getattr(self.request.user, "team_profile", None)
        if profile is None:
            raise NotFound("Aucun profil d'équipe lié à ce compte.")
        return profile


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
class TrackView(APIView):
    """POST /api/analytics/track/ — à appeler par le front à chaque page, SEULEMENT si le visiteur a accepté."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "analytics"

    def post(self, request):
        serializer = TrackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if not data.pop("consent"):
            return Response(status=status.HTTP_204_NO_CONTENT)  # pas de consentement : rien n'est enregistré

        ip = client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        Visit.objects.create(
            **data,
            **geolocate(ip, request),
            **parse_user_agent(ua),
            ip_masked=mask_ip(ip),
            user_agent=ua[:300],
        )
        return Response(status=status.HTTP_201_CREATED)


class AnalyticsSummaryView(APIView):
    """GET /api/analytics/summary/?days=30  (réservé au personnel : Authorization: Token ...)"""

    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            days = max(int(request.query_params.get("days", 30)), 1)
        except ValueError:
            raise ValidationError({"days": "Doit être un entier."})
        since = timezone.now() - timedelta(days=days)
        visits = Visit.objects.filter(created_at__gte=since)

        def top(field, n=10):
            return list(
                visits.exclude(**{field: ""}).values(field).annotate(count=Count("id")).order_by("-count")[:n]
            )

        return Response({
            "period_days": days,
            "total_visits": visits.count(),
            "unique_visitors": visits.values("visitor_id").distinct().count(),
            "by_country": top("country_code"),
            "by_city": list(
                visits.exclude(city="").values("city", "country_code").annotate(count=Count("id")).order_by("-count")[:10]
            ),
            "by_device": top("device_type"),
            "by_browser": top("browser"),
            "by_os": top("os"),
            "by_language": top("language"),
            "by_timezone": top("timezone"),
            "top_pages": top("path"),
            "top_referrers": top("referrer"),
            "per_day": list(
                visits.annotate(day=TruncDate("created_at")).values("day").annotate(count=Count("id")).order_by("day")
            ),
        })


class VisitListView(generics.ListAPIView):
    """GET /api/analytics/visits/  (personnel uniquement, paginé)"""

    serializer_class = VisitSerializer
    permission_classes = [IsAdminUser]
    queryset = Visit.objects.all()

    class pagination_class(PageNumberPagination):
        page_size = 50
        page_size_query_param = "page_size"
        max_page_size = 200
