"""python manage.py seed_demo  — crée des données d'exemple pour tester le front."""
import io
import random
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image

from club.models import (
    Category, ClubSettings, ContentBlock, Event, MediaItem, Partner, Project, ProjectCategory,
    TeamMember, Technology,
)


def dark_image(seed, size=(1200, 700)):
    rnd = random.Random(seed)
    base = tuple(rnd.randint(10, 60) for _ in range(3))
    im = Image.new("RGB", size, base)
    px = im.load()
    for y in range(size[1]):
        for x in range(0, size[0]):
            k = int(40 * x / size[0])
            px[x, y] = (base[0] + k // 3, base[1] + k // 2, base[2] + k)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80)
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = "Crée des données de démonstration."

    def handle(self, *args, **options):
        User = get_user_model()
        cats = {}
        for name, icon in [("Programmation", "code"), ("Cybersécurité", "shield"), ("IA", "brain"),
                           ("Robotique", "bot"), ("Web", "globe")]:
            cats[name], _ = Category.objects.get_or_create(name=name, defaults={"icon": icon})
        pcats = {}
        for i, (name, icon) in enumerate([("Web", "code"), ("Mobile", "smartphone"), ("IA / Data", "brain"),
                                          ("Réseaux", "network"), ("Sécurité", "shield"), ("Autres", "layers")]):
            pcats[name], _ = ProjectCategory.objects.get_or_create(name=name, defaults={"icon": icon, "order": i})
        techs = {}
        for name, icon in [("Python", "terminal"), ("React", "layers"), ("Django", "server"), ("Arduino", "cpu")]:
            techs[name], _ = Technology.objects.get_or_create(name=name, defaults={"icon": icon})

        members = []
        for i, (username, first, last, role) in enumerate([
            ("alice", "Alice", "Martin", "Présidente"),
            ("bob", "Bob", "Durand", "Vice-président"),
            ("chloe", "Chloé", "Nguyen", "Responsable technique"),
        ]):
            user, created = User.objects.get_or_create(username=username, defaults={"first_name": first, "last_name": last})
            if created:
                user.set_password("demo12345")
                user.save()
            member, m_created = TeamMember.objects.get_or_create(user=user, defaults={
                "role": role, "bio": f"{first} fait partie du bureau du club.", "order": i,
                "skills": "Python, Django, React", "joined_year": 2024,
            })
            if m_created:
                member.photo.save(f"{username}.jpg", dark_image(username, (400, 400)), save=True)
            members.append(member)

        today = timezone.localdate()
        samples = [
            ("Soirée de lancement du club", "Lancement", Event.Kind.EVENT, 7, None),
            ("Hackathon de fin de session", "Hackathon", Event.Kind.COMPETITION, 21, None),
            ("Atelier Git et GitHub", "Atelier Git", Event.Kind.WORKSHOP, 3, None),
            ("Atelier Python débutant", "Python débutant", Event.Kind.WORKSHOP, -10, None),
            ("Formation Django", "Formation Django", Event.Kind.TRAINING, -3, 10),
            ("Formation Cybersécurité", "Cybersécurité", Event.Kind.TRAINING, -60, -40),
            ("Concours de programmation", "Concours", Event.Kind.COMPETITION, -30, None),
            ("Atelier électronique", "Électronique", Event.Kind.WORKSHOP, None, None),  # date à confirmer
        ]
        for name, title, kind, offset, end_offset in samples:
            ev, created = Event.objects.get_or_create(name=name, defaults={
                "title": title[:20], "description": f"{name} — ouvert à tous les étudiants.",
                "kind": kind,
                "date": today + timedelta(days=offset) if offset is not None else None,
                "end_date": today + timedelta(days=end_offset) if end_offset is not None else None,
                "start_time": time(14, 0) if offset is not None else None,
                "end_time": time(16, 0) if offset is not None else None,
                "room": "Salle B-204" if offset is not None else "", "capacity": 40 if offset is not None else None,
            })
            if created:
                ev.categories.set(random.sample(list(cats.values()), 2))

        for i, title in enumerate(["Site web du club", "Robot suiveur de ligne", "Assistant IA étudiant"]):
            proj, created = Project.objects.get_or_create(title=title, defaults={
                "description": f"{title} : un projet réalisé par les membres du club.",
                "date": today - timedelta(days=30 * (i + 1)),
                "status": Project.Status.COMPLETED if i else Project.Status.IN_PROGRESS,
                "is_recruiting": i == 0, "other_contributors": "Dylan, Emma",
                "category": [pcats["Web"], pcats["Mobile"], pcats["IA / Data"]][i],
            })
            if created:
                proj.image.save(f"project{i}.jpg", dark_image(title), save=True)
                proj.technologies.set(random.sample(list(techs.values()), 2))
                proj.members.set(members[: i + 1])

        if not MediaItem.objects.exists():
            for i in range(4):
                item = MediaItem(caption=f"Photo d'un évènement du club #{i + 1}")
                item.file.save(f"demo{i}.jpg", dark_image(f"media{i}"), save=False)
                item.save()

        if not ContentBlock.objects.exists():
            S = ContentBlock.Section
            for i, (sec, title, desc, icon) in enumerate([
                (S.VALUE, "Collaboration", "Travailler ensemble pour aller plus loin.", "users"),
                (S.VALUE, "Innovation", "Explorer, créer et oser proposer.", "graduation-cap"),
                (S.VALUE, "Apprentissage", "Apprendre chaque jour et partager nos savoirs.", "lightbulb"),
                (S.VALUE, "Entraide", "S'entraider et grandir en communauté.", "handshake"),
                (S.WHY, "Développez vos compétences", "", "trending-up"),
                (S.WHY, "Rencontrez des passionnés", "", "user"),
                (S.WHY, "Travaillez sur des projets concrets", "", "code"),
                (S.WHY, "Booster votre avenir professionnel", "", "briefcase"),
                (S.PERK, "Activités régulières", "De nouvelles activités chaque semaine.", "calendar"),
                (S.PERK, "Ouvert à tous", "Étudiants de tous niveaux sont les bienvenus.", "user"),
            ]):
                ContentBlock.objects.create(section=sec, title=title, description=desc, icon=icon, order=i)

        for name in ["Cégep Tech", "Acme Cloud", "OpenLab"]:
            Partner.objects.get_or_create(name=name)
        settings_obj = ClubSettings.load()
        settings_obj.active_members = 157
        settings_obj.about_text = "Le club INFO DEP a pour mission de promouvoir la culture informatique."
        settings_obj.mission = "Promouvoir la culture informatique et favoriser l'entraide entre étudiants."
        settings_obj.contact_email = "info.dep@example.com"
        settings_obj.save()
        self.stdout.write(self.style.SUCCESS("Données de démonstration créées (mot de passe des comptes : demo12345)."))
