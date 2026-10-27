# API du club informatique (Django REST framework)

📘 **Documentation complète de l'API et des actions : [`docs/API.md`](docs/API.md)**

## Installation

```bash
python -m venv .venv && source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations club   # si vous l'aviez déjà fait : relancez-la, elle ajoute les nouveaux champs
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo          # optionnel : données d'exemple
python manage.py runserver
```

- **Saisie des données** : http://localhost:8000/admin/ (évènements, projets, équipe, bibliothèque, inscriptions, etc.)
- **API** : http://localhost:8000/api/  (navigable dans le navigateur)
- Les fichiers envoyés sont servis sur `/media/` (en développement).

Variables d'environnement utiles : `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` (0 en production), `DJANGO_ALLOWED_HOSTS`,
`DJANGO_CORS_ORIGINS` (adresse du front, ex. `http://localhost:5173`), `DJANGO_TIME_ZONE`,
`GEOIP_DB_PATH`, `TRUST_X_FORWARDED_FOR`.

## Icônes Lucide

Chaque catégorie, technologie, type d'évènement, type de média et statistique contient :

```json
"icon": { "name": "calendar-days", "component": "CalendarDays" }
```

```jsx
import * as Icons from "lucide-react";
const Icon = Icons[item.icon.component];   // <Icon size={20} />
// ou : import { DynamicIcon } from "lucide-react/dynamic"; <DynamicIcon name={item.icon.name} />
```

La liste des icônes disponibles dans l'admin est dans `club/icons.py` (ajoutez-en au besoin).

## Endpoints (lecture publique, sauf mention)

| # | Méthode & URL | Rôle |
|---|---|---|
| 1 | `GET /api/events/recent/?limit=3` | N derniers évènements (sans `limit` : tous). Filtre `?kind=` |
| 1 | `GET /api/events/` | Liste. Filtres `?kind=event\|workshop\|training\|competition` `?category=<slug>` `?status=upcoming\|ongoing\|finished` `?limit=` |
| 1 | `GET /api/events/upcoming/?limit=5` | Évènements à venir |
| 2 | `GET /api/projects/recent/?limit=3` | N projets récents (sans `limit` : tous) |
| 2 | `GET /api/projects/` · `GET /api/projects/<id>/` | Liste / détail |
| 3 | `GET /api/stats/` | Estimations : `{"display": "150+", "value": 150, "title": ..., "icon": ...}` pour `active_members`, `completed_projects`, `events_per_year`, `partners` |
| 4 | `GET /api/team/` | Membres importants de l'équipe |
| 5 | `GET /api/library/?type=image\|video&page=1&page_size=24` | Bibliothèque (paginée) |
| 7 | `GET /api/events/overview/?limit=10&recent_days=60` | `upcoming_events`, `workshops{upcoming,ongoing,recently_completed}`, `trainings{upcoming,ongoing,completed}`, `competitions{upcoming,ongoing,completed}` |
| 8 | `GET /api/categories/` | Liste des catégories (avec icône) |
| 8 | `GET /api/events/by-category/?kind=&limit=` | Évènements regroupés par catégorie |
| 9 | `POST /api/analytics/track/` | Enregistre une page vue (public, avec consentement) |
| 9 | `GET /api/analytics/summary/?days=30` | Statistiques agrégées (**personnel uniquement**) |
| 9 | `GET /api/analytics/visits/` | Visites détaillées, paginées (**personnel uniquement**) |
| – | `GET /api/partners/` | Partenaires |
| – | `GET /api/projects/?category=web&search=django&technology=React` | Liste filtrée (onglets + barre de recherche de la page Projets) |
| – | `GET /api/projects/summary/` | « En chiffres » de la page Projets (valeurs exactes + icônes) |
| – | `GET /api/project-categories/` | Onglets Web / Mobile / IA-Data… avec icône et nombre de projets |
| – | `GET /api/technologies/` | Bloc « Technologies utilisées » (avec nombre de projets) |
| – | `GET /api/site/` | Textes éditables : à propos, mission, valeurs, « Pourquoi participer ? », atouts, coordonnées |
| – | `POST /api/contact/` | Bouton « Nous contacter » `{name, email, subject?, message}` (5/heure/IP) |
| – | `POST /api/registrations/` | Inscription (voir ci-dessous) |
| – | `POST /api/auth/login/` · `GET/PATCH /api/auth/me/` | Connexion d'un membre (token) et modification de son profil |

### Inscriptions

```json
POST /api/registrations/
{ "event": 4, "full_name": "Jean Dupont", "email": "jean@ecole.ca", "phone": "", "message": "" }   // évènement/atelier/formation/compétition
{ "project": 2, "full_name": "...", "email": "..." }                                               // projet (doit recruter)
{ "full_name": "...", "email": "..." }                                                              // adhésion au club
```
Refus (400) si : inscriptions fermées, évènement terminé, complet, projet qui ne recrute pas, courriel déjà inscrit.
Limite : 10 inscriptions/heure par adresse IP. Les inscriptions se gèrent dans l'admin (confirmer, annuler, export CSV).

### Analytics

Appelez depuis le front à chaque changement de page, **uniquement après acceptation du visiteur** :

```js
fetch(`${API}/api/analytics/track/`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    visitor_id: localStorage.getItem("vid") ?? (localStorage.vid = crypto.randomUUID()),
    path: location.pathname,
    referrer: document.referrer,
    language: navigator.language,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    screen_width: screen.width, screen_height: screen.height,
    consent: true,
  }),
});
```
Le serveur ajoute pays/région/ville (si `GEOIP_DB_PATH` pointe vers GeoLite2-City.mmdb, sinon pays via Cloudflare
ou aucun), appareil, navigateur et système. L'adresse IP n'est **jamais stockée en entier** (dernier octet masqué).
Prévoyez une bannière de consentement et une politique de confidentialité (Loi 25 au Québec / RGPD en Europe).

### Profil des membres

`POST /api/auth/login/ {"username","password"}` → `{"token": "...", "member": {...}}`, puis
`Authorization: Token <token>` pour `GET/PATCH /api/auth/me/` (bio, photo, compétences, liens).
Pour les endpoints réservés au personnel (analytics), le compte doit avoir « statut équipe » dans l'admin.

## Correspondance avec les pages du front

| Page / bloc | Appel |
|---|---|
| Accueil – Prochains évènements (4 cartes) | `GET /api/events/upcoming/?kind=event&limit=4` |
| Accueil – À propos + 4 chiffres | `GET /api/site/` + `GET /api/stats/` |
| Accueil – Projets récents | `GET /api/projects/recent/?limit=4` |
| Le club – mission, valeurs | `GET /api/site/` |
| Le club – équipe | `GET /api/team/` (photo/présentation vides = affichez votre texte par défaut) |
| Le club – bibliothèque + « Voir plus » | `GET /api/library/?page_size=6`, puis `?page=2`… |
| Activités – onglets | `GET /api/events/?kind=event\|workshop\|training\|competition` (ou `/api/events/overview/` en un seul appel) |
| Activités – bouton « S'inscrire » | `POST /api/registrations/ {event: id, ...}` |
| Activités – « Pourquoi participer ? » et bandeau | `GET /api/site/` (`why_participate`, `perks`) |
| Projets – onglets, recherche, chiffres, technologies | `/api/project-categories/`, `/api/projects/?search=`, `/api/projects/summary/`, `/api/technologies/` |
| Rejoindre le club | `POST /api/registrations/` sans `event` ni `project` |
| Nous contacter | `POST /api/contact/` |

**« À confirmer »** : pour un évènement, laissez vide la date, l'horaire, la salle ou les places dans l'admin ;
l'API renvoie alors `null` (et `status: "to_be_confirmed"` si la date manque) et le front affiche « à confirmer ».

## Règles de saisie (admin)

- Évènement : `title` ≤ 20 caractères, `description` ≤ 100 caractères, heure de fin après l'heure de début. Image optionnelle.
  Pour une formation sur plusieurs jours, renseignez « Date de fin ».
- Projet : choisissez une catégorie (Web, Mobile…). « Taille de l'équipe » se calcule seule si vide. L'image doit être **sombre** (un avertissement s'affiche dans l'admin si elle semble claire).
- Équipe : créez d'abord l'utilisateur, puis le « Membre de l'équipe » lié à ce compte.
- Membres actifs : saisis à la main dans « Réglages du club » ; les autres statistiques sont calculées.
