"""Icônes Lucide proposées dans l'admin.

Chaque donnée envoyée au front contient ``{"name": "calendar-days", "component": "CalendarDays"}`` :
- ``name``      -> nom kebab-case (``<DynamicIcon name="..."/>`` de lucide-react/dynamic, lucide-static, etc.)
- ``component`` -> nom du composant React (``import * as Icons from "lucide-react"; Icons[component]``)

Pour ajouter une icône : ajoutez une ligne ci-dessous (nom exact sur https://lucide.dev/icons),
puis ``python manage.py makemigrations``.
"""

ICON_CHOICES = [
    ("calendar", "Calendrier"),
    ("calendar-days", "Calendrier (jours)"),
    ("code", "Code"),
    ("terminal", "Terminal"),
    ("cpu", "Processeur"),
    ("circuit-board", "Circuit électronique"),
    ("binary", "Binaire"),
    ("database", "Base de données"),
    ("server", "Serveur"),
    ("cloud", "Cloud"),
    ("globe", "Web / Globe"),
    ("network", "Réseau"),
    ("wifi", "Wi-Fi"),
    ("shield", "Sécurité"),
    ("lock", "Cadenas"),
    ("bug", "Bug"),
    ("git-branch", "Git"),
    ("brain", "Intelligence artificielle"),
    ("bot", "Robot"),
    ("cog", "Engrenage"),
    ("wrench", "Clé"),
    ("hammer", "Marteau"),
    ("smartphone", "Mobile"),
    ("laptop", "Ordinateur portable"),
    ("monitor", "Écran"),
    ("gamepad-2", "Jeu vidéo"),
    ("palette", "Design"),
    ("pen-tool", "Dessin vectoriel"),
    ("layers", "Couches"),
    ("blocks", "Blocs"),
    ("puzzle", "Puzzle"),
    ("lightbulb", "Idée"),
    ("rocket", "Fusée"),
    ("sparkles", "Étincelles"),
    ("zap", "Éclair"),
    ("star", "Étoile"),
    ("heart", "Cœur"),
    ("trophy", "Trophée"),
    ("medal", "Médaille"),
    ("award", "Récompense"),
    ("graduation-cap", "Formation"),
    ("school", "École"),
    ("presentation", "Présentation"),
    ("book-open", "Livre"),
    ("flask-conical", "Expérience"),
    ("microscope", "Recherche"),
    ("users", "Groupe"),
    ("user", "Personne"),
    ("handshake", "Partenariat"),
    ("megaphone", "Annonce"),
    ("camera", "Photo"),
    ("image", "Image"),
    ("video", "Vidéo"),
    ("film", "Film"),
    ("mic", "Micro"),
    ("music", "Musique"),
    ("radio", "Radio"),
    ("mail", "Courriel"),
    ("phone", "Téléphone"),
    ("map-pin", "Lieu"),
    ("clock", "Horloge"),
    ("folder-kanban", "Projets"),
    ("building", "Bâtiment"),
    ("layout-grid", "Grille"),
    ("briefcase", "Mallette / carrière"),
    ("trending-up", "Progression"),
    ("target", "Objectif"),
    ("book", "Livre fermé"),
]

EVENT_KIND_ICONS = {
    "event": "calendar",
    "workshop": "wrench",
    "training": "book-open",
    "competition": "trophy",
}

MEDIA_TYPE_ICONS = {"image": "image", "video": "video"}

STAT_ICONS = {
    "active_members": "network",
    "completed_projects": "book",
    "events_per_year": "calendar-days",
    "partners": "users",
}

PROJECT_SUMMARY_ICONS = {
    "projects": "layout-grid",
    "categories": "layers",
    "team_participations": "users",
    "technologies": "code",
}


def to_pascal(name: str) -> str:
    """'gamepad-2' -> 'Gamepad2' (nom du composant lucide-react)."""
    return "".join(part.capitalize() for part in name.split("-"))


def icon_payload(name: str):
    if not name:
        return None
    return {"name": name, "component": to_pascal(name)}
