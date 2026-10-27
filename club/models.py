from datetime import datetime, time
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from .icons import ICON_CHOICES


# ---------------------------------------------------------------------------
# Référentiels (catégories, technologies)
# ---------------------------------------------------------------------------
class Category(models.Model):
    name = models.CharField("Nom", max_length=60, unique=True)
    slug = models.SlugField("Slug", max_length=70, unique=True, blank=True)
    icon = models.CharField(
        "Icône Lucide", max_length=40, choices=ICON_CHOICES, default="calendar",
        help_text="Icône affichée par le front (Lucide).",
    )

    class Meta:
        verbose_name = "Catégorie"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Technology(models.Model):
    name = models.CharField("Nom", max_length=60, unique=True)
    icon = models.CharField("Icône Lucide", max_length=40, choices=ICON_CHOICES, default="code")

    class Meta:
        verbose_name = "Technologie"
        ordering = ["name"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Évènements (évènements, ateliers, formations, compétitions)
# ---------------------------------------------------------------------------
class Event(models.Model):
    class Kind(models.TextChoices):
        EVENT = "event", "Évènement"
        WORKSHOP = "workshop", "Atelier"
        TRAINING = "training", "Formation"
        COMPETITION = "competition", "Compétition"

    name = models.CharField("Nom de l'évènement", max_length=150)
    title = models.CharField("Titre (affiché, 20 caractères max)", max_length=20)
    description = models.CharField("Description (100 caractères max)", max_length=100)
    kind = models.CharField("Type", max_length=20, choices=Kind.choices, default=Kind.EVENT)
    categories = models.ManyToManyField(Category, verbose_name="Catégories", related_name="events", blank=True)

    image = models.ImageField("Image", upload_to="events/", null=True, blank=True)
    date = models.DateField("Date (ou date de début)", null=True, blank=True, help_text="Vide = « date à confirmer ».")
    end_date = models.DateField(
        "Date de fin", null=True, blank=True,
        help_text="Laisser vide si l'évènement se termine le même jour (utile pour les formations).",
    )
    start_time = models.TimeField("Heure de début", null=True, blank=True, help_text="Vide = « horaire à confirmer ».")
    end_time = models.TimeField("Heure de fin", null=True, blank=True)
    room = models.CharField("Salle", max_length=100, blank=True, help_text="Vide = « lieu à confirmer ».")

    capacity = models.PositiveIntegerField("Places disponibles", null=True, blank=True, help_text="Vide = « places à confirmer ».")
    registration_open = models.BooleanField("Inscriptions ouvertes", default=True)

    # Calculés automatiquement à partir de date / heures (permet des filtres rapides)
    starts_at = models.DateTimeField(null=True, blank=True, editable=False, db_index=True)
    ends_at = models.DateTimeField(null=True, blank=True, editable=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Évènement"
        ordering = ["-starts_at"]

    def clean(self):
        if self.end_date and not self.date:
            raise ValidationError({"date": "Renseignez la date de début."})
        if self.date and self.start_time and self.end_time:
            last_day = self.end_date or self.date
            if last_day < self.date:
                raise ValidationError({"end_date": "La date de fin précède la date de début."})
            if last_day == self.date and self.end_time <= self.start_time:
                raise ValidationError({"end_time": "L'heure de fin doit être après l'heure de début."})

    def save(self, *args, **kwargs):
        tz = timezone.get_current_timezone()
        self.starts_at = self.ends_at = None
        if self.date:  # sans date : « à confirmer »
            start_t = self.start_time or time(0, 0)
            end_t = self.end_time or time(23, 59, 59)
            self.starts_at = timezone.make_aware(datetime.combine(self.date, start_t), tz)
            self.ends_at = timezone.make_aware(datetime.combine(self.end_date or self.date, end_t), tz)
        super().save(*args, **kwargs)

    @property
    def status(self):
        if self.starts_at is None:
            return "to_be_confirmed"
        now = timezone.now()
        if now < self.starts_at:
            return "upcoming"
        if now <= self.ends_at:
            return "ongoing"
        return "finished"

    def __str__(self):
        return f"{self.title} ({self.date})"


# ---------------------------------------------------------------------------
# Équipe
# ---------------------------------------------------------------------------
class TeamMember(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="team_profile",
        verbose_name="Compte de connexion",
        help_text="Créez d'abord l'utilisateur (Authentification > Utilisateurs), puis liez-le ici.",
    )
    photo = models.ImageField("Photo", upload_to="team/", null=True, blank=True)
    role = models.CharField("Rôle", max_length=100)
    bio = models.TextField("Présentation", blank=True)
    skills = models.CharField("Compétences", max_length=255, blank=True, help_text="Séparées par des virgules.")
    joined_year = models.PositiveSmallIntegerField("Membre depuis (année)", null=True, blank=True)
    public_email = models.EmailField("Courriel public", blank=True)
    linkedin = models.URLField("LinkedIn", blank=True)
    github = models.URLField("GitHub", blank=True)
    order = models.PositiveSmallIntegerField("Ordre d'affichage", default=0)
    is_public = models.BooleanField("Visible sur le site", default=True)

    class Meta:
        verbose_name = "Membre de l'équipe"
        verbose_name_plural = "Équipe"
        ordering = ["order", "id"]

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.get_username()

    @property
    def skills_list(self):
        return [s.strip() for s in self.skills.split(",") if s.strip()]

    def __str__(self):
        return f"{self.full_name} – {self.role}"


# ---------------------------------------------------------------------------
# Projets
# ---------------------------------------------------------------------------
class ProjectCategory(models.Model):
    """Catégories de projets (Web, Mobile, IA / Data, Réseaux, Sécurité, Autres...)."""

    name = models.CharField("Nom", max_length=60, unique=True)
    slug = models.SlugField("Slug", max_length=70, unique=True, blank=True)
    icon = models.CharField("Icône Lucide", max_length=40, choices=ICON_CHOICES, default="layers")
    order = models.PositiveSmallIntegerField("Ordre d'affichage", default=0)

    class Meta:
        verbose_name = "Catégorie de projet"
        verbose_name_plural = "Catégories de projets"
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Project(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "En cours"
        COMPLETED = "completed", "Terminé"

    image = models.ImageField(
        "Image du projet (sombre de préférence)", upload_to="projects/",
        help_text="IMPORTANT : choisir une image SOMBRE pour un meilleur rendu sur le site "
                  "(le texte est affiché par-dessus).",
    )
    title = models.CharField("Titre", max_length=100)
    description = models.TextField("Description")
    category = models.ForeignKey(
        ProjectCategory, verbose_name="Catégorie", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="projects",
    )
    technologies = models.ManyToManyField(Technology, verbose_name="Technologies utilisées", blank=True)
    members = models.ManyToManyField(
        TeamMember, verbose_name="Membres de l'équipe sur le projet", related_name="projects", blank=True,
    )
    other_contributors = models.CharField(
        "Autres participants", max_length=255, blank=True, help_text="Noms séparés par des virgules.",
    )
    team_size = models.PositiveSmallIntegerField(
        "Taille de l'équipe", null=True, blank=True,
        help_text="Laisser vide pour la calculer (membres choisis + autres participants).",
    )
    date = models.DateField("Date du projet")
    status = models.CharField("Statut", max_length=20, choices=Status.choices, default=Status.COMPLETED)
    is_recruiting = models.BooleanField("Recherche des participants (inscriptions ouvertes)", default=False)
    link = models.URLField("Lien (dépôt, démo)", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Projet"
        ordering = ["-date", "-id"]

    @property
    def contributors(self):
        return [n.strip() for n in self.other_contributors.split(",") if n.strip()]

    @property
    def team_count(self):
        if self.team_size is not None:
            return self.team_size
        return len(self.members.all()) + len(self.contributors)

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# Bibliothèque (images / vidéos)
# ---------------------------------------------------------------------------
IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp", "gif", "avif"]
VIDEO_EXTENSIONS = ["mp4", "webm", "mov", "m4v"]


class MediaItem(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Vidéo"

    file = models.FileField(
        "Fichier (image ou vidéo)", upload_to="library/%Y/%m/",
        validators=[FileExtensionValidator(IMAGE_EXTENSIONS + VIDEO_EXTENSIONS)],
    )
    media_type = models.CharField("Type", max_length=10, choices=MediaType.choices, editable=False)
    caption = models.CharField("Légende", max_length=200, help_text="Petite phrase expliquant l'image ou la vidéo.")
    thumbnail = models.ImageField("Miniature (vidéos)", upload_to="library/thumbs/", null=True, blank=True)
    taken_on = models.DateField("Date de la prise", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Média"
        verbose_name_plural = "Bibliothèque"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        ext = Path(self.file.name).suffix.lower().lstrip(".")
        self.media_type = self.MediaType.VIDEO if ext in VIDEO_EXTENSIONS else self.MediaType.IMAGE
        super().save(*args, **kwargs)

    def __str__(self):
        return self.caption[:50]


# ---------------------------------------------------------------------------
# Partenaires et réglages du club
# ---------------------------------------------------------------------------
class Partner(models.Model):
    name = models.CharField("Nom", max_length=100)
    logo = models.ImageField("Logo", upload_to="partners/", blank=True)
    website = models.URLField("Site web", blank=True)
    is_active = models.BooleanField("Actif", default=True)

    class Meta:
        verbose_name = "Partenaire"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ClubSettings(models.Model):
    """Une seule ligne : chiffres saisis à la main (les autres stats sont calculées)."""

    active_members = models.PositiveIntegerField(
        "Nombre de membres actifs", default=0, help_text="Un chiffre approximatif suffit (affiché ex. « 150+ »).",
    )

    about_text = models.TextField("Texte « À propos du club » (accueil)", blank=True)
    mission = models.TextField("Notre mission (page Le club)", blank=True)
    contact_email = models.EmailField("Courriel de contact", blank=True)
    contact_phone = models.CharField("Téléphone", max_length=30, blank=True)
    address = models.CharField("Adresse / local", max_length=200, blank=True)

    class Meta:
        verbose_name = "Réglages du club"
        verbose_name_plural = "Réglages du club"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return "Réglages du club"


class ContentBlock(models.Model):
    """Petits blocs de texte avec icône affichés sur le site (valeurs, « Pourquoi participer ? », atouts)."""

    class Section(models.TextChoices):
        VALUE = "value", "Nos valeurs (page Le club)"
        WHY = "why_participate", "Pourquoi participer ? (page Activités)"
        PERK = "perk", "Bandeau d'atouts (bas de la page Activités)"

    section = models.CharField("Section", max_length=20, choices=Section.choices)
    title = models.CharField("Titre", max_length=80)
    description = models.CharField("Description", max_length=200, blank=True)
    icon = models.CharField("Icône Lucide", max_length=40, choices=ICON_CHOICES, default="star")
    order = models.PositiveSmallIntegerField("Ordre d'affichage", default=0)
    is_active = models.BooleanField("Visible", default=True)

    class Meta:
        verbose_name = "Bloc de contenu"
        verbose_name_plural = "Blocs de contenu"
        ordering = ["section", "order", "id"]

    def __str__(self):
        return f"[{self.get_section_display()}] {self.title}"


class ContactMessage(models.Model):
    """Messages envoyés via « Nous contacter »."""

    name = models.CharField("Nom", max_length=150)
    email = models.EmailField("Courriel")
    subject = models.CharField("Sujet", max_length=150, blank=True)
    message = models.TextField("Message", max_length=2000)
    is_read = models.BooleanField("Lu", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Message de contact"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} – {self.subject or 'sans sujet'}"


# ---------------------------------------------------------------------------
# Inscriptions
# ---------------------------------------------------------------------------
class Registration(models.Model):
    """Inscription à un évènement/atelier/formation/compétition, à un projet,
    ou (sans cible) au club lui-même."""

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        CONFIRMED = "confirmed", "Confirmée"
        CANCELLED = "cancelled", "Annulée"

    event = models.ForeignKey(Event, null=True, blank=True, on_delete=models.CASCADE, related_name="registrations")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.CASCADE, related_name="registrations")
    full_name = models.CharField("Nom complet", max_length=150)
    email = models.EmailField("Courriel")
    phone = models.CharField("Téléphone", max_length=30, blank=True)
    message = models.TextField("Message", max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Inscription"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(event__isnull=False, project__isnull=False),
                name="registration_single_target",
            ),
            models.UniqueConstraint(
                fields=["event", "email"], condition=Q(event__isnull=False), name="uniq_registration_event_email",
            ),
            models.UniqueConstraint(
                fields=["project", "email"], condition=Q(project__isnull=False), name="uniq_registration_project_email",
            ),
            models.UniqueConstraint(
                fields=["email"], condition=Q(event__isnull=True, project__isnull=True),
                name="uniq_registration_club_email",
            ),
        ]

    @property
    def kind(self):
        if self.event_id:
            return self.event.kind
        if self.project_id:
            return "project"
        return "club"

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        target = self.event or self.project or "Club"
        return f"{self.full_name} → {target}"


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
class Visit(models.Model):
    """Une page vue. L'adresse IP n'est jamais stockée en entier (masquée)."""

    visitor_id = models.CharField(max_length=64, db_index=True)
    path = models.CharField(max_length=500)
    referrer = models.CharField(max_length=500, blank=True)
    language = models.CharField(max_length=20, blank=True)
    timezone = models.CharField(max_length=64, blank=True)
    screen_width = models.PositiveIntegerField(null=True, blank=True)
    screen_height = models.PositiveIntegerField(null=True, blank=True)

    country = models.CharField(max_length=80, blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    region = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    ip_masked = models.CharField(max_length=45, blank=True)

    device_type = models.CharField(max_length=20, blank=True)
    browser = models.CharField(max_length=40, blank=True)
    os = models.CharField(max_length=40, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Visite"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.path} ({self.created_at:%Y-%m-%d %H:%M})"
