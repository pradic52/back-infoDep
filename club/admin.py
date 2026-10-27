import csv

from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils.html import format_html
from PIL import Image, ImageStat

from .models import (
    Category, ClubSettings, ContactMessage, ContentBlock, Event, MediaItem, Partner, Project,
    ProjectCategory, Registration, TeamMember, Technology, Visit,
)

admin.site.site_header = "Club informatique – Administration"
admin.site.site_title = "Club informatique"
admin.site.index_title = "Gestion du contenu du site"

STATUS_LABELS = {"upcoming": "À venir", "ongoing": "En cours", "finished": "Terminé", "to_be_confirmed": "À confirmer"}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "order")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "icon", "order", "is_active")
    list_filter = ("section", "is_active")
    list_editable = ("order", "is_active")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "email", "subject", "is_read")
    list_filter = ("is_read",)
    search_fields = ("name", "email", "subject", "message")
    list_editable = ("is_read",)

    def has_add_permission(self, request):
        return False


@admin.register(Technology)
class TechnologyAdmin(admin.ModelAdmin):
    list_display = ("name", "icon")
    search_fields = ("name",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "date", "start_time", "end_time", "room", "state", "registrations_count")
    list_filter = ("kind", "categories", "date", "registration_open")
    search_fields = ("name", "title", "room")
    filter_horizontal = ("categories",)
    date_hierarchy = "date"
    fieldsets = (
        ("Identité", {"fields": ("kind", "name", "title", "description", "image", "categories")}),
        ("Date et lieu (laisser vide = « à confirmer »)", {
            "fields": ("date", "end_date", "start_time", "end_time", "room"),
        }),
        ("Inscriptions", {"fields": ("registration_open", "capacity")}),
    )

    @admin.display(description="État")
    def state(self, obj):
        return STATUS_LABELS[obj.status]

    @admin.display(description="Inscrits")
    def registrations_count(self, obj):
        return obj.registrations.exclude(status=Registration.Status.CANCELLED).count()


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("full_name", "role", "order", "is_public")
    list_editable = ("order", "is_public")
    search_fields = ("user__username", "user__first_name", "user__last_name", "role")
    autocomplete_fields = ("user",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("preview", "title", "category", "date", "status", "is_recruiting")
    list_filter = ("category", "status", "is_recruiting", "technologies")
    search_fields = ("title", "description")
    filter_horizontal = ("technologies", "members")
    date_hierarchy = "date"

    @admin.display(description="Image")
    def preview(self, obj):
        return format_html('<img src="{}" style="height:40px;border-radius:4px">', obj.image.url) if obj.image else "-"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if "image" in form.changed_data and obj.image:
            try:
                with Image.open(obj.image.path) as im:
                    brightness = ImageStat.Stat(im.convert("L")).mean[0]
                if brightness > 110:
                    self.message_user(
                        request,
                        f"Attention : l'image semble claire (luminosité {brightness:.0f}/255). "
                        "Une image sombre donne un meilleur rendu sur le site.",
                        messages.WARNING,
                    )
            except Exception:
                pass


@admin.register(MediaItem)
class MediaItemAdmin(admin.ModelAdmin):
    list_display = ("preview", "caption", "media_type", "taken_on", "created_at")
    list_filter = ("media_type",)
    search_fields = ("caption",)
    readonly_fields = ("media_type",)

    @admin.display(description="Aperçu")
    def preview(self, obj):
        if obj.media_type == MediaItem.MediaType.IMAGE and obj.file:
            return format_html('<img src="{}" style="height:40px;border-radius:4px">', obj.file.url)
        return "🎬" if obj.file else "-"


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "website", "is_active")
    list_editable = ("is_active",)


@admin.register(ClubSettings)
class ClubSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not ClubSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "target", "status", "created_at")
    list_filter = ("status", "event__kind", "event", "project")
    search_fields = ("full_name", "email")
    actions = ["confirm", "cancel", "export_csv"]

    @admin.display(description="Inscrit à")
    def target(self, obj):
        return str(obj.event or obj.project or "Le club")

    @admin.action(description="Confirmer les inscriptions sélectionnées")
    def confirm(self, request, queryset):
        queryset.update(status=Registration.Status.CONFIRMED)

    @admin.action(description="Annuler les inscriptions sélectionnées")
    def cancel(self, request, queryset):
        queryset.update(status=Registration.Status.CANCELLED)

    @admin.action(description="Exporter en CSV")
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="inscriptions.csv"'
        writer = csv.writer(response)
        writer.writerow(["Nom", "Courriel", "Téléphone", "Inscrit à", "Statut", "Date", "Message"])
        for r in queryset.select_related("event", "project"):
            writer.writerow([r.full_name, r.email, r.phone, self.target(r), r.get_status_display(),
                             r.created_at.strftime("%Y-%m-%d %H:%M"), r.message])
        return response


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("created_at", "path", "country_code", "city", "device_type", "browser", "os")
    list_filter = ("country_code", "device_type", "browser", "os")
    search_fields = ("path", "city", "referrer")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
