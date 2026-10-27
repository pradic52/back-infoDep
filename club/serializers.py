from django.utils import timezone
from rest_framework import serializers

from .icons import EVENT_KIND_ICONS, MEDIA_TYPE_ICONS, icon_payload
from .models import (
    Category, ContactMessage, ContentBlock, Event, MediaItem, Partner, Project, ProjectCategory,
    Registration, TeamMember, Technology, Visit,
)


class IconMixin(serializers.Serializer):
    icon = serializers.SerializerMethodField()

    def get_icon(self, obj):
        return icon_payload(obj.icon)


class CategorySerializer(IconMixin, serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon"]


class TechnologySerializer(IconMixin, serializers.ModelSerializer):
    class Meta:
        model = Technology
        fields = ["id", "name", "icon"]


class TechnologyUsageSerializer(TechnologySerializer):
    project_count = serializers.IntegerField(read_only=True)

    class Meta(TechnologySerializer.Meta):
        fields = ["id", "name", "icon", "project_count"]


class ProjectCategorySerializer(IconMixin, serializers.ModelSerializer):
    class Meta:
        model = ProjectCategory
        fields = ["id", "name", "slug", "icon"]


class ProjectCategoryCountSerializer(ProjectCategorySerializer):
    project_count = serializers.IntegerField(read_only=True)

    class Meta(ProjectCategorySerializer.Meta):
        fields = ["id", "name", "slug", "icon", "project_count"]


class EventSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    kind_icon = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()
    status = serializers.ReadOnlyField()
    spots_left = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id", "name", "title", "description", "image", "kind", "kind_label", "kind_icon", "icon", "categories",
            "date", "end_date", "start_time", "end_time", "room",
            "status", "registration_open", "capacity", "spots_left",
        ]

    def get_kind_icon(self, obj):
        return icon_payload(EVENT_KIND_ICONS.get(obj.kind))

    def get_icon(self, obj):
        """Icône de la carte : celle de la 1re catégorie, sinon celle du type d'activité."""
        first = next(iter(obj.categories.all()), None)
        return icon_payload(first.icon if first else EVENT_KIND_ICONS.get(obj.kind))

    def get_spots_left(self, obj):
        if obj.capacity is None:
            return None
        taken = getattr(obj, "taken", None)
        if taken is None:
            taken = obj.registrations.exclude(status=Registration.Status.CANCELLED).count()
        return max(obj.capacity - taken, 0)


class TeamMemberMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = TeamMember
        fields = ["id", "full_name", "role", "photo"]


class TeamMemberSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    skills = serializers.SerializerMethodField()
    email = serializers.EmailField(source="public_email", read_only=True)

    class Meta:
        model = TeamMember
        fields = [
            "id", "full_name", "role", "photo", "bio", "skills", "joined_year",
            "email", "linkedin", "github",
        ]

    def get_skills(self, obj):
        return obj.skills_list


class MeSerializer(serializers.ModelSerializer):
    """Profil modifiable par le membre connecté (rôle et ordre restent gérés par l'admin)."""

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = TeamMember
        fields = [
            "id", "full_name", "role", "photo", "bio", "skills", "joined_year",
            "public_email", "linkedin", "github",
        ]
        read_only_fields = ["role"]


class ProjectSerializer(serializers.ModelSerializer):
    technologies = TechnologySerializer(many=True, read_only=True)
    members = TeamMemberMiniSerializer(many=True, read_only=True)
    contributors = serializers.ListField(child=serializers.CharField(), read_only=True)
    category = ProjectCategorySerializer(read_only=True)
    team_size = serializers.IntegerField(source="team_count", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "image", "title", "description", "category", "technologies", "members", "contributors", "team_size",
            "date", "status", "status_label", "is_recruiting", "link",
        ]


class MediaItemSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="media_type", read_only=True)
    type_icon = serializers.SerializerMethodField()

    class Meta:
        model = MediaItem
        fields = ["id", "file", "type", "type_icon", "caption", "thumbnail", "taken_on"]

    def get_type_icon(self, obj):
        return icon_payload(MEDIA_TYPE_ICONS.get(obj.media_type))


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ["id", "name", "logo", "website"]


class RegistrationSerializer(serializers.ModelSerializer):
    """POST {event: id} | {project: id} | aucun des deux = inscription au club."""

    class Meta:
        model = Registration
        fields = ["id", "event", "project", "full_name", "email", "phone", "message", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]
        extra_kwargs = {"event": {"required": False}, "project": {"required": False}}

    def validate(self, attrs):
        event = attrs.get("event")
        project = attrs.get("project")
        email = attrs["email"].strip().lower()

        if event and project:
            raise serializers.ValidationError("Choisissez un évènement OU un projet, pas les deux.")

        if event:
            if not event.registration_open:
                raise serializers.ValidationError({"event": "Les inscriptions sont fermées pour cet évènement."})
            if event.ends_at and event.ends_at < timezone.now():
                raise serializers.ValidationError({"event": "Cet évènement est déjà terminé."})
            if event.capacity is not None:
                taken = event.registrations.exclude(status=Registration.Status.CANCELLED).count()
                if taken >= event.capacity:
                    raise serializers.ValidationError({"event": "Il n'y a plus de places disponibles."})
            exists = Registration.objects.filter(event=event, email=email)
        elif project:
            if not project.is_recruiting:
                raise serializers.ValidationError({"project": "Ce projet ne recrute pas pour le moment."})
            exists = Registration.objects.filter(project=project, email=email)
        else:
            exists = Registration.objects.filter(event__isnull=True, project__isnull=True, email=email)

        if exists.exists():
            raise serializers.ValidationError({"email": "Cette adresse est déjà inscrite."})
        return attrs


class TrackSerializer(serializers.Serializer):
    visitor_id = serializers.CharField(max_length=64)
    path = serializers.CharField(max_length=500)
    referrer = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    language = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    timezone = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    screen_width = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=20000)
    screen_height = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=20000)
    consent = serializers.BooleanField()


class VisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit
        exclude = ["user_agent"]


class ContentBlockSerializer(IconMixin, serializers.ModelSerializer):
    class Meta:
        model = ContentBlock
        fields = ["id", "title", "description", "icon"]


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "subject", "message"]
