# Documentation de l'API – Club informatique INFO DEP

Version du document : 1.0 · Backend : Django + Django REST framework · Base de l'API : `/api/`

> Cette documentation décrit **tous les endpoints**, les **formats de réponse**, les **règles de saisie**, les
> **actions** possibles (côté visiteur, côté membre et côté administrateur) et la façon de brancher le front-end.

## Sommaire

1. [Principes généraux](#1-principes-généraux)
2. [Démarrage rapide](#2-démarrage-rapide)
3. [Icônes Lucide](#3-icônes-lucide)
4. [Référence des endpoints](#4-référence-des-endpoints)
   - [4.1 Évènements](#41-évènements)
   - [4.2 Catégories d'évènements](#42-catégories-dévènements)
   - [4.3 Projets](#43-projets)
   - [4.4 Équipe](#44-équipe)
   - [4.5 Bibliothèque](#45-bibliothèque)
   - [4.6 Statistiques](#46-statistiques)
   - [4.7 Contenu du site](#47-contenu-du-site)
   - [4.8 Partenaires](#48-partenaires)
   - [4.9 Inscriptions](#49-inscriptions)
   - [4.10 Contact](#410-contact)
   - [4.11 Authentification et profil](#411-authentification-et-profil)
   - [4.12 Analytics](#412-analytics)
5. [Les actions](#5-les-actions)
   - [5.1 Actions du visiteur (front-end)](#51-actions-du-visiteur-front-end)
   - [5.2 Actions du membre connecté](#52-actions-du-membre-connecté)
   - [5.3 Actions de l'administrateur (interface `/admin/`)](#53-actions-de-ladministrateur-interface-admin)
6. [Règles de saisie](#6-règles-de-saisie)
7. [Correspondance pages du front → API](#7-correspondance-pages-du-front--api)
8. [Exemples de code front-end](#8-exemples-de-code-front-end)
9. [Configuration et déploiement](#9-configuration-et-déploiement)
10. [Vie privée et analytics](#10-vie-privée-et-analytics)
11. [Aide-mémoire](#11-aide-mémoire)

---

## 1. Principes généraux

| Sujet | Règle |
|---|---|
| URL de base | `http://localhost:8000/api/` en développement |
| Format | JSON (UTF-8). Les envois de fichiers (photo) utilisent `multipart/form-data`. |
| Lecture | **Publique** : aucun jeton requis (sauf analytics détaillés et profil). |
| Écriture | Le contenu (évènements, projets…) se saisit dans l'**admin Django**. L'API publique n'accepte en écriture que : inscriptions, contact, tracking, connexion et modification de son propre profil. |
| Authentification | Jeton : en-tête `Authorization: Token <votre_jeton>` (voir [4.11](#411-authentification-et-profil)). |
| Pagination | **Aucune** sauf `/library/` et `/analytics/visits/` (format `count / next / previous / results`). |
| Dates et heures | Date `2026-11-11` · heure `14:30:00` · date-heure ISO 8601. Le fuseau est celui de `DJANGO_TIME_ZONE` (défaut `America/Toronto`). |
| Images / fichiers | URL **absolue** (`http://localhost:8000/media/...`) ou `null` si absent. |
| Valeurs inconnues | Date, horaire, salle, places d'un évènement : `null` = « à confirmer ». |
| CORS | Origines autorisées via `DJANGO_CORS_ORIGINS` (défaut : `localhost:5173`, `127.0.0.1:5173`, `localhost:3000`). |
| Limitation de débit | Voir tableau ci-dessous. Dépassement : HTTP `429`. |

### Limites de débit (par adresse IP)

| Endpoint | Limite |
|---|---|
| `POST /registrations/` | 10 par heure |
| `POST /contact/` | 5 par heure |
| `POST /auth/login/` | 20 par heure |
| `POST /analytics/track/` | 300 par heure |

### Codes de réponse

| Code | Signification |
|---|---|
| `200` | Succès (lecture, modification) |
| `201` | Créé (inscription, contact, visite) |
| `204` | Accepté sans contenu (tracking sans consentement : rien n'est enregistré) |
| `400` | Données invalides (détail par champ) |
| `401` | Jeton absent ou invalide |
| `403` | Compte connecté mais droits insuffisants (non « équipe ») |
| `404` | Ressource inexistante (ou profil d'équipe non lié au compte) |
| `429` | Trop de requêtes |

### Format des erreurs

```json
// 400 – erreur de champ
{ "email": ["Cette adresse est déjà inscrite."] }

// 400 – erreur générale
{ "non_field_errors": ["Choisissez un évènement OU un projet, pas les deux."] }

// 400 – paramètre ?limit= invalide
{ "limit": "Doit être un entier." }

// 404 / 401 / 403 / 429
{ "detail": "Not found." }
```

### Paramètre `limit`

Disponible sur les listes d'évènements et de projets : `?limit=N` (entier ≥ 1, **plafonné à 100**).
**Sans `limit`, tous les éléments sont renvoyés.** Valeur invalide (`abc`, `0`) → `400`.

### Valeurs d'énumération

| Champ | Valeurs |
|---|---|
| Évènement `kind` | `event` (Évènement), `workshop` (Atelier), `training` (Formation), `competition` (Compétition) |
| Évènement `status` | `upcoming` (à venir), `ongoing` (en cours), `finished` (terminé), `to_be_confirmed` (date non fixée) |
| Projet `status` | `in_progress` (En cours), `completed` (Terminé) |
| Média `type` | `image`, `video` |
| Inscription `status` | `pending` (en attente), `confirmed`, `cancelled` |

---

## 2. Démarrage rapide

```bash
python -m venv .venv && source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations club
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo        # données d'exemple (optionnel)
python manage.py runserver
```

| Adresse | Contenu |
|---|---|
| `http://localhost:8000/admin/` | Saisie des données |
| `http://localhost:8000/api/` | Racine de l'API (navigable dans le navigateur) |
| `http://localhost:8000/media/...` | Fichiers envoyés (en développement) |

Test rapide :

```bash
curl http://localhost:8000/api/stats/
curl "http://localhost:8000/api/events/recent/?limit=3"
```

Comptes créés par `seed_demo` : `alice`, `bob`, `chloe` (mot de passe `demo12345`).

---

## 3. Icônes Lucide

Chaque objet qui porte une icône la renvoie sous cette forme :

```json
"icon": { "name": "calendar-days", "component": "CalendarDays" }
```

| Clé | Usage |
|---|---|
| `name` | Nom kebab-case : `<DynamicIcon name={icon.name} />` (`lucide-react/dynamic`) ou lucide-static. |
| `component` | Nom du composant React : `import * as Icons from "lucide-react"; const Icon = Icons[icon.component];` |

### Où apparaissent des icônes

| Objet | Champ(s) | Choix de l'icône |
|---|---|---|
| Catégorie d'évènement | `icon` | dans l'admin |
| Catégorie de projet | `icon` | dans l'admin |
| Technologie | `icon` | dans l'admin |
| Bloc de contenu (valeurs, atouts…) | `icon` | dans l'admin |
| Évènement | `icon` (celle de sa 1re catégorie par ordre alphabétique, sinon celle du type) et `kind_icon` | automatique |
| Média | `type_icon` | automatique |
| Statistiques d'accueil | `icon` | fixe |
| « En chiffres » des projets | `icon` | fixe |

Icônes fixes :

| Élément | Icône |
|---|---|
| Évènement `event` | `calendar` |
| Atelier `workshop` | `wrench` |
| Formation `training` | `book-open` |
| Compétition `competition` | `trophy` |
| Média `image` / `video` | `image` / `video` |
| Membres actifs | `network` |
| Projets réalisés | `book` |
| Évènements / an | `calendar-days` |
| Partenaires | `users` |
| Projets présentés | `layout-grid` |
| Catégories | `layers` |
| Participations d'équipe | `users` |
| Technologies citées | `code` |

### Icônes disponibles dans l'admin

| Nom (`icon.name`) | Composant (`icon.component`) | Libellé admin |
|---|---|---|
| `calendar` | `Calendar` | Calendrier |
| `calendar-days` | `CalendarDays` | Calendrier (jours) |
| `code` | `Code` | Code |
| `terminal` | `Terminal` | Terminal |
| `cpu` | `Cpu` | Processeur |
| `circuit-board` | `CircuitBoard` | Circuit électronique |
| `binary` | `Binary` | Binaire |
| `database` | `Database` | Base de données |
| `server` | `Server` | Serveur |
| `cloud` | `Cloud` | Cloud |
| `globe` | `Globe` | Web / Globe |
| `network` | `Network` | Réseau |
| `wifi` | `Wifi` | Wi-Fi |
| `shield` | `Shield` | Sécurité |
| `lock` | `Lock` | Cadenas |
| `bug` | `Bug` | Bug |
| `git-branch` | `GitBranch` | Git |
| `brain` | `Brain` | Intelligence artificielle |
| `bot` | `Bot` | Robot |
| `cog` | `Cog` | Engrenage |
| `wrench` | `Wrench` | Clé |
| `hammer` | `Hammer` | Marteau |
| `smartphone` | `Smartphone` | Mobile |
| `laptop` | `Laptop` | Ordinateur portable |
| `monitor` | `Monitor` | Écran |
| `gamepad-2` | `Gamepad2` | Jeu vidéo |
| `palette` | `Palette` | Design |
| `pen-tool` | `PenTool` | Dessin vectoriel |
| `layers` | `Layers` | Couches |
| `blocks` | `Blocks` | Blocs |
| `puzzle` | `Puzzle` | Puzzle |
| `lightbulb` | `Lightbulb` | Idée |
| `rocket` | `Rocket` | Fusée |
| `sparkles` | `Sparkles` | Étincelles |
| `zap` | `Zap` | Éclair |
| `star` | `Star` | Étoile |
| `heart` | `Heart` | Cœur |
| `trophy` | `Trophy` | Trophée |
| `medal` | `Medal` | Médaille |
| `award` | `Award` | Récompense |
| `graduation-cap` | `GraduationCap` | Formation |
| `school` | `School` | École |
| `presentation` | `Presentation` | Présentation |
| `book-open` | `BookOpen` | Livre |
| `flask-conical` | `FlaskConical` | Expérience |
| `microscope` | `Microscope` | Recherche |
| `users` | `Users` | Groupe |
| `user` | `User` | Personne |
| `handshake` | `Handshake` | Partenariat |
| `megaphone` | `Megaphone` | Annonce |
| `camera` | `Camera` | Photo |
| `image` | `Image` | Image |
| `video` | `Video` | Vidéo |
| `film` | `Film` | Film |
| `mic` | `Mic` | Micro |
| `music` | `Music` | Musique |
| `radio` | `Radio` | Radio |
| `mail` | `Mail` | Courriel |
| `phone` | `Phone` | Téléphone |
| `map-pin` | `MapPin` | Lieu |
| `clock` | `Clock` | Horloge |
| `folder-kanban` | `FolderKanban` | Projets |
| `building` | `Building` | Bâtiment |
| `layout-grid` | `LayoutGrid` | Grille |
| `briefcase` | `Briefcase` | Mallette / carrière |
| `trending-up` | `TrendingUp` | Progression |
| `target` | `Target` | Objectif |
| `book` | `Book` | Livre fermé |

Pour en ajouter : éditez `ICON_CHOICES` dans `club/icons.py` (nom exact sur <https://lucide.dev/icons>), puis
`python manage.py makemigrations club && python manage.py migrate`.

---

## 4. Référence des endpoints

Vue d'ensemble :

| Méthode | URL | Accès | Rôle |
|---|---|---|---|
| GET | `/events/` | public | Liste filtrable des évènements |
| GET | `/events/<id>/` | public | Détail d'un évènement |
| GET | `/events/recent/` | public | Évènements récents |
| GET | `/events/upcoming/` | public | Évènements à venir |
| GET | `/events/overview/` | public | Vue globale (à venir, ateliers, formations, compétitions) |
| GET | `/events/by-category/` | public | Évènements regroupés par catégorie |
| GET | `/categories/` | public | Catégories d'évènements |
| GET | `/projects/` | public | Liste filtrable des projets |
| GET | `/projects/<id>/` | public | Détail d'un projet |
| GET | `/projects/recent/` | public | Projets récents |
| GET | `/projects/summary/` | public | « En chiffres » de la page Projets |
| GET | `/project-categories/` | public | Catégories de projets (onglets) |
| GET | `/technologies/` | public | Technologies utilisées |
| GET | `/team/` · `/team/<id>/` | public | Équipe |
| GET | `/library/` · `/library/<id>/` | public | Bibliothèque (paginée) |
| GET | `/stats/` | public | Statistiques estimées (« 150+ ») |
| GET | `/site/` | public | Textes et blocs éditables |
| GET | `/partners/` | public | Partenaires |
| POST | `/registrations/` | public | S'inscrire |
| POST | `/contact/` | public | Envoyer un message |
| POST | `/auth/login/` | public | Connexion d'un membre |
| GET · PUT · PATCH | `/auth/me/` | membre connecté | Son profil |
| POST | `/analytics/track/` | public | Enregistrer une visite |
| GET | `/analytics/summary/` | **personnel** | Statistiques agrégées |
| GET | `/analytics/visits/` | **personnel** | Visites détaillées |

---

### 4.1 Évènements

Un « évènement » regroupe les 4 types : évènements, ateliers, formations, compétitions (champ `kind`).

#### Objet Évènement

```json
{
  "id": 4,
  "name": "Atelier de programmation pour débutants",
  "title": "Atelier Python",
  "description": "Initiation à Python pour débutants",
  "image": "http://localhost:8000/media/events/python.png",
  "kind": "workshop",
  "kind_label": "Atelier",
  "kind_icon": { "name": "wrench", "component": "Wrench" },
  "icon": { "name": "code", "component": "Code" },
  "categories": [
    { "id": 1, "name": "Programmation", "slug": "programmation",
      "icon": { "name": "code", "component": "Code" } }
  ],
  "date": "2026-11-11",
  "end_date": null,
  "start_time": "14:30:00",
  "end_time": "16:30:00",
  "room": "Salle 011",
  "status": "upcoming",
  "registration_open": true,
  "capacity": 30,
  "spots_left": 22
}
```

| Champ | Type | Description |
|---|---|---|
| `id` | entier | Identifiant |
| `name` | texte | Nom complet de l'évènement (150 car. max) |
| `title` | texte | Titre court affiché sur les cartes (**20 car. max**) |
| `description` | texte | Description (**100 car. max**) |
| `image` | URL ou `null` | Image de la carte |
| `kind`, `kind_label`, `kind_icon` | | Type, son libellé français, son icône |
| `icon` | objet | Icône de la carte (1re catégorie, sinon icône du type) |
| `categories` | liste | Catégories avec icône |
| `date` | date ou `null` | Date (ou début). `null` = **date à confirmer** |
| `end_date` | date ou `null` | Fin, pour les évènements sur plusieurs jours (formations) |
| `start_time`, `end_time` | heure ou `null` | `null` = **horaire à confirmer** |
| `room` | texte | Salle. Chaîne vide = **lieu à confirmer** |
| `status` | texte | `upcoming`, `ongoing`, `finished`, `to_be_confirmed` |
| `registration_open` | booléen | Inscriptions ouvertes ? |
| `capacity` | entier ou `null` | Places totales. `null` = **places à confirmer** |
| `spots_left` | entier ou `null` | Places restantes (inscriptions non annulées déduites) ; `null` si `capacity` est `null` |

#### `GET /events/`

Liste des évènements. Ordre : plus récent d'abord ; avec `status=upcoming` : le plus proche d'abord.

| Paramètre | Valeurs | Description |
|---|---|---|
| `kind` | `event`, `workshop`, `training`, `competition` | Filtre par type |
| `category` | slug de catégorie | Filtre par catégorie |
| `status` | `upcoming`, `ongoing`, `finished`, `to_be_confirmed` | Filtre par état |
| `limit` | entier | Nombre maximum |

```bash
curl "http://localhost:8000/api/events/?kind=workshop&status=upcoming&limit=3"
```

Réponse : tableau d'objets Évènement.

#### `GET /events/<id>/`

Un objet Évènement, ou `404`.

#### `GET /events/recent/`

**Évènements récents** : ceux déjà commencés (en cours ou terminés), du plus récent au plus ancien.
Les évènements sans date n'y figurent pas.

| Paramètre | Description |
|---|---|
| `limit` | Nombre d'évènements ; **absent = tous** |
| `kind` | Restreindre à un type |

```bash
curl "http://localhost:8000/api/events/recent/?limit=5"
```

#### `GET /events/upcoming/`

Évènements **à venir** (date future, **ou date à confirmer**), le plus proche en premier ; les dates à confirmer en dernier.

| Paramètre | Description |
|---|---|
| `limit` | Nombre d'évènements ; absent = tous |
| `kind` | Restreindre à un type (ex. `event` pour l'accueil) |

#### `GET /events/overview/`

Tout ce qu'il faut pour la page Activités, en **un seul appel**.

| Paramètre | Défaut | Description |
|---|---|---|
| `limit` | `10` | Nombre maximum **par liste** |
| `recent_days` | `60` | Fenêtre de « réalisé récemment » pour les ateliers (jours) |

```json
{
  "upcoming_events": [ /* évènements de type event à venir */ ],
  "workshops": {
    "upcoming": [],
    "ongoing": [],
    "recently_completed": []
  },
  "trainings": {
    "upcoming": [],
    "ongoing": [],
    "completed": []
  },
  "competitions": {
    "upcoming": [],
    "ongoing": [],
    "completed": []
  }
}
```

| Liste | Contenu |
|---|---|
| `upcoming_events` | Évènements (`kind=event`) à venir ou à date à confirmer |
| `workshops.upcoming` / `ongoing` | Ateliers à venir / en cours |
| `workshops.recently_completed` | Ateliers terminés depuis moins de `recent_days` jours |
| `trainings.ongoing` / `completed` | Formations en cours / toutes les formations terminées |
| `competitions.upcoming` / `ongoing` / `completed` | Compétitions à venir / en cours / terminées |

#### `GET /events/by-category/`

Évènements regroupés par catégorie (les catégories sans évènement sont omises).

| Paramètre | Description |
|---|---|
| `kind` | Restreindre à un type |
| `limit` | Nombre d'évènements **par catégorie** (le `count` reste le total) |

```json
[
  {
    "category": { "id": 1, "name": "Programmation", "slug": "programmation",
                  "icon": { "name": "code", "component": "Code" } },
    "count": 5,
    "events": [ /* objets Évènement */ ]
  }
]
```

---

### 4.2 Catégories d'évènements

#### `GET /categories/`

```json
[
  { "id": 1, "name": "Programmation", "slug": "programmation", "icon": { "name": "code", "component": "Code" } },
  { "id": 2, "name": "Cybersécurité", "slug": "cybersecurite", "icon": { "name": "shield", "component": "Shield" } }
]
```

Triées par nom. Le `slug` sert de filtre : `/events/?category=programmation`.

---

### 4.3 Projets

#### Objet Projet

```json
{
  "id": 7,
  "image": "http://localhost:8000/media/projects/plateforme.jpg",
  "title": "Plateforme de gestion des évènements",
  "description": "Une application web pour organiser les évènements du club et gérer les inscriptions.",
  "category": { "id": 1, "name": "Web", "slug": "web", "icon": { "name": "code", "component": "Code" } },
  "technologies": [
    { "id": 1, "name": "React", "icon": { "name": "layers", "component": "Layers" } },
    { "id": 2, "name": "Django", "icon": { "name": "server", "component": "Server" } }
  ],
  "members": [
    { "id": 1, "full_name": "Alice Martin", "role": "Présidente", "photo": "http://localhost:8000/media/team/alice.jpg" }
  ],
  "contributors": ["Dylan", "Emma"],
  "team_size": 4,
  "date": "2025-05-14",
  "status": "completed",
  "status_label": "Terminé",
  "is_recruiting": false,
  "link": "https://github.com/club/plateforme"
}
```

| Champ | Description |
|---|---|
| `image` | Image du projet (doit être **sombre** pour un bon rendu) |
| `category` | Catégorie (badge sur l'image : « Web », « Mobile »…). `null` si non renseignée |
| `technologies` | Technologies utilisées (pastilles) |
| `members` | Membres de l'équipe du club travaillant sur le projet |
| `contributors` | Autres participants (liste de noms) |
| `team_size` | Taille de l'équipe : valeur saisie, sinon `members` + `contributors` |
| `date` | Date du projet. Pour afficher « Mai 2025 » : `new Date(date).toLocaleDateString("fr-CA", { month: "long", year: "numeric" })` |
| `status` / `status_label` | `in_progress` / `completed` et libellé |
| `is_recruiting` | `true` si des inscriptions au projet sont ouvertes |
| `link` | Lien externe (dépôt, démo) ou chaîne vide |

#### `GET /projects/`

Liste, du plus récent au plus ancien.

| Paramètre | Description |
|---|---|
| `category` | Slug de catégorie de projet (`web`, `mobile`, `ia-data`, `reseaux`, `securite`, `autres`) |
| `technology` | Nom exact (insensible à la casse) : `?technology=React` |
| `search` | Recherche dans titre, description, technologies et catégorie |
| `limit` | Nombre maximum |

Les filtres se combinent : `/projects/?category=web&search=django`.

#### `GET /projects/<id>/`

Un objet Projet, ou `404`.

#### `GET /projects/recent/`

Projets les plus récents. `?limit=N` ; **absent = tous les projets**.

```bash
curl "http://localhost:8000/api/projects/recent/?limit=4"
```

#### `GET /projects/summary/`

Bloc « EN CHIFFRES » de la page Projets (valeurs **exactes**).

```json
{
  "projects":            { "title": "projets présentés",      "value": 8,  "icon": { "name": "layout-grid", "component": "LayoutGrid" } },
  "categories":          { "title": "catégories",             "value": 6,  "icon": { "name": "layers", "component": "Layers" } },
  "team_participations": { "title": "participations d'équipe","value": 29, "icon": { "name": "users", "component": "Users" } },
  "technologies":        { "title": "technologies citées",    "value": 18, "icon": { "name": "code", "component": "Code" } }
}
```

#### `GET /project-categories/`

Onglets de filtre de la page Projets (« Tous les projets » est à ajouter côté front).

```json
[
  { "id": 1, "name": "Web", "slug": "web", "icon": { "name": "code", "component": "Code" }, "project_count": 3 }
]
```

Ordre : champ « Ordre d'affichage » de l'admin.

#### `GET /technologies/`

Technologies utilisées par au moins un projet (bloc « TECHNOLOGIES UTILISÉES »).

```json
[ { "id": 1, "name": "React", "icon": { "name": "layers", "component": "Layers" }, "project_count": 4 } ]
```

---

### 4.4 Équipe

#### `GET /team/` · `GET /team/<id>/`

Membres marqués « Visible sur le site », triés par « Ordre d'affichage ».

```json
{
  "id": 1,
  "full_name": "Alice Martin",
  "role": "Présidente",
  "photo": "http://localhost:8000/media/team/alice.jpg",
  "bio": "Étudiante en 2e année, passionnée de cybersécurité.",
  "skills": ["Python", "Django", "Réseaux"],
  "joined_year": 2024,
  "email": "alice@exemple.ca",
  "linkedin": "https://linkedin.com/in/alice",
  "github": "https://github.com/alice"
}
```

| Champ | Notes |
|---|---|
| `full_name` | Prénom + nom du compte ; à défaut, le nom d'utilisateur |
| `photo`, `bio` | Peuvent être `null` / vides : le front affiche alors son texte par défaut (« Rôle à préciser », etc.) |
| `skills` | Liste (saisie séparée par des virgules dans l'admin) |
| `email` | Courriel **public** choisi par le membre (pas son courriel de connexion) |

---

### 4.5 Bibliothèque

#### `GET /library/` · `GET /library/<id>/`

Images et vidéos, de la plus récente à la plus ancienne. **Paginée.**

| Paramètre | Défaut | Description |
|---|---|---|
| `type` | tous | `image` ou `video` |
| `page` | `1` | Numéro de page |
| `page_size` | `24` | Taille de page (max 100) |

```json
{
  "count": 42,
  "next": "http://localhost:8000/api/library/?page=2&page_size=6",
  "previous": null,
  "results": [
    {
      "id": 12,
      "file": "http://localhost:8000/media/library/2026/09/atelier.jpg",
      "type": "image",
      "type_icon": { "name": "image", "component": "Image" },
      "caption": "Atelier Python du 11 novembre",
      "thumbnail": null,
      "taken_on": "2025-11-11"
    }
  ]
}
```

Pour une vidéo : `type: "video"`, `file` = fichier vidéo (`<video src>`), `thumbnail` = miniature si fournie
(affichez le bouton ▶ et l'étiquette « Vidéo »).
Formats acceptés : images `jpg, jpeg, png, webp, gif, avif` ; vidéos `mp4, webm, mov, m4v`.

Bouton « Voir plus de souvenirs » : suivez `next` jusqu'à ce qu'il soit `null`.

---

### 4.6 Statistiques

#### `GET /stats/`

Chiffres **estimés** pour l'accueil (« 150+ », « 20+ »).

```json
{
  "active_members":     { "title": "Membres actifs",     "value": 150, "display": "150+", "icon": { "name": "network", "component": "Network" } },
  "completed_projects": { "title": "Projets réalisés",   "value": 20,  "display": "20+",  "icon": { "name": "book", "component": "Book" } },
  "events_per_year":    { "title": "Évènements par an",  "value": 15,  "display": "15+",  "icon": { "name": "calendar-days", "component": "CalendarDays" } },
  "partners":           { "title": "Partenaires",        "value": 5,   "display": "5+",   "icon": { "name": "users", "component": "Users" } }
}
```

| Clé | Calcul |
|---|---|
| `active_members` | Valeur saisie dans « Réglages du club » ; à défaut, nombre de membres d'équipe visibles |
| `completed_projects` | Projets au statut « Terminé » |
| `events_per_year` | Nombre d'évènements ÷ nombre d'années distinctes avec évènement |
| `partners` | Partenaires actifs |

**Règle d'arrondi** (on arrondit toujours **vers le bas**, puis on ajoute `+`) :

| Nombre réel | Pas | Exemple |
|---|---|---|
| 0 | – | `0` → `"0"` |
| 1 – 9 | 1 | `7` → `"7+"` |
| 10 – 49 | 5 | `23` → `"20+"` |
| 50 – 99 | 10 | `87` → `"80+"` |
| 100 – 499 | 50 | `157` → `"150+"` |
| 500 – 999 | 100 | `640` → `"600+"` |
| 1000 et plus | 500 | `1730` → `"1500+"` |

`display` est le texte prêt à afficher ; `value` est le nombre arrondi (pour une animation de compteur).

---

### 4.7 Contenu du site

#### `GET /site/`

Textes modifiables dans l'admin (pas besoin de modifier le code du front).

```json
{
  "about": "Le club INFO DEP a pour mission de promouvoir la culture informatique…",
  "mission": "Promouvoir la culture informatique, développer les compétences techniques…",
  "values": [
    { "id": 1, "title": "Collaboration", "description": "Travailler ensemble pour aller plus loin.",
      "icon": { "name": "users", "component": "Users" } }
  ],
  "why_participate": [
    { "id": 5, "title": "Développez vos compétences", "description": "",
      "icon": { "name": "trending-up", "component": "TrendingUp" } }
  ],
  "perks": [
    { "id": 9, "title": "Activités régulières", "description": "De nouvelles activités chaque semaine.",
      "icon": { "name": "calendar", "component": "Calendar" } }
  ],
  "contact": { "email": "info.dep@exemple.ca", "phone": "", "address": "" }
}
```

| Clé | Où l'afficher |
|---|---|
| `about` | Accueil – « À PROPOS DU CLUB » |
| `mission` | Page Le club – « NOTRE MISSION » |
| `values` | Page Le club – « NOS VALEURS » |
| `why_participate` | Page Activités – « Pourquoi participer ? » |
| `perks` | Page Activités – bandeau du bas |
| `contact` | Pied de page / « Nous contacter » |

Seuls les blocs cochés « Visible » sont renvoyés, triés par « Ordre d'affichage ».

---

### 4.8 Partenaires

#### `GET /partners/`

```json
[ { "id": 1, "name": "Cégep Tech", "logo": "http://localhost:8000/media/partners/logo.png", "website": "https://exemple.ca" } ]
```

Seuls les partenaires « Actifs » sont renvoyés.

---

### 4.9 Inscriptions

#### `POST /registrations/`

Une seule route pour toutes les inscriptions. La **cible** est déterminée par le corps de la requête :

| Corps | Type d'inscription |
|---|---|
| `{"event": <id>, ...}` | Évènement, atelier, formation **ou** compétition |
| `{"project": <id>, ...}` | Projet (qui doit recruter : `is_recruiting = true`) |
| ni `event` ni `project` | Adhésion au club (« S'inscrire au club ») |

| Champ | Obligatoire | Description |
|---|---|---|
| `event` | non | Id d'un évènement |
| `project` | non | Id d'un projet |
| `full_name` | **oui** | Nom complet (150 car. max) |
| `email` | **oui** | Courriel valide (normalisé en minuscules) |
| `phone` | non | Téléphone |
| `message` | non | Message (500 car. max) |

```bash
curl -X POST http://localhost:8000/api/registrations/ \
  -H "Content-Type: application/json" \
  -d '{"event": 4, "full_name": "Jean Dupont", "email": "jean@ecole.ca"}'
```

**Réponse `201`** :

```json
{ "id": 31, "event": 4, "project": null, "full_name": "Jean Dupont", "email": "jean@ecole.ca",
  "phone": "", "message": "", "status": "pending", "created_at": "2026-10-02T14:05:12.331Z" }
```

L'inscription est créée au statut `pending`; un administrateur la confirme ensuite (voir [5.3](#53-actions-de-ladministrateur-interface-admin)).

**Refus `400`** :

| Situation | Réponse |
|---|---|
| `event` **et** `project` fournis | `non_field_errors` : « Choisissez un évènement OU un projet, pas les deux. » |
| Inscriptions fermées | `event` : « Les inscriptions sont fermées pour cet évènement. » |
| Évènement terminé | `event` : « Cet évènement est déjà terminé. » |
| Évènement complet | `event` : « Il n'y a plus de places disponibles. » |
| Projet qui ne recrute pas | `project` : « Ce projet ne recrute pas pour le moment. » |
| Courriel déjà inscrit à la même cible | `email` : « Cette adresse est déjà inscrite. » |
| `event` / `project` inexistant | message standard « clé primaire invalide » |
| Champ requis manquant | `full_name` / `email` : « Ce champ est obligatoire. » |

Un même courriel peut s'inscrire à plusieurs cibles différentes, mais une seule fois par cible.
Limite : 10 requêtes/heure/IP (`429` au-delà).

---

### 4.10 Contact

#### `POST /contact/`

Bouton « Nous contacter ». Le message est lu dans l'admin (« Messages de contact »).

| Champ | Obligatoire | Limite |
|---|---|---|
| `name` | **oui** | 150 |
| `email` | **oui** | courriel valide |
| `subject` | non | 150 |
| `message` | **oui** | 2000 |

```bash
curl -X POST http://localhost:8000/api/contact/ -H "Content-Type: application/json" \
  -d '{"name":"Jean","email":"jean@ecole.ca","subject":"Partenariat","message":"Bonjour…"}'
```

Réponse `201` : les champs enregistrés avec leur `id`. Limite : 5/heure/IP.

---

### 4.11 Authentification et profil

Chaque membre de l'équipe est lié à un **compte** Django (créé par l'administrateur).

#### `POST /auth/login/`

```json
// requête
{ "username": "alice", "password": "demo12345" }

// réponse 200
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "member": { "id": 1, "full_name": "Alice Martin", "role": "Présidente", "photo": null, "bio": "",
              "skills": "Python, Django", "joined_year": 2024, "public_email": "", "linkedin": "", "github": "" }
}
```

`member` vaut `null` si le compte n'est lié à aucun profil d'équipe. Mauvais identifiants : `400`
(`non_field_errors`). Limite : 20/heure/IP.

Pour les requêtes suivantes : `Authorization: Token <token>`.

#### `GET /auth/me/`

Retourne le profil du membre connecté (mêmes champs que `member` ci-dessus). `401` sans jeton ;
`404` si le compte n'a pas de profil d'équipe.

#### `PATCH /auth/me/` (ou `PUT`)

Modifie son propre profil.

| Modifiable | Non modifiable (admin seulement) |
|---|---|
| `photo`, `bio`, `skills` (texte séparé par des virgules), `joined_year`, `public_email`, `linkedin`, `github` | `role`, ordre d'affichage, visibilité, nom |

```bash
curl -X PATCH http://localhost:8000/api/auth/me/ \
  -H "Authorization: Token <token>" \
  -F "bio=Passionnée de cybersécurité" -F "photo=@moi.jpg"
```

> Le nom (`full_name`) vient du compte utilisateur : il se modifie dans l'admin.

---

### 4.12 Analytics

Collecte de statistiques de visite, **avec consentement du visiteur** (voir [10](#10-vie-privée-et-analytics)).

#### `POST /analytics/track/`

À appeler par le front à chaque changement de page, **uniquement si le visiteur a accepté**.

| Champ | Obligatoire | Description |
|---|---|---|
| `visitor_id` | **oui** | Identifiant anonyme généré par le front (UUID, conservé en `localStorage`) |
| `path` | **oui** | Page vue (`/projets`) |
| `consent` | **oui** | `true` si le visiteur a accepté. `false` → **rien n'est enregistré** (réponse `204`) |
| `referrer` | non | `document.referrer` |
| `language` | non | `navigator.language` |
| `timezone` | non | `Intl.DateTimeFormat().resolvedOptions().timeZone` |
| `screen_width`, `screen_height` | non | Dimensions de l'écran |

Réponses : `201` (enregistré, corps vide), `204` (pas de consentement), `400` (données invalides).

Le serveur ajoute lui-même : pays / région / ville (si GeoIP configuré, sinon pays Cloudflare si disponible),
type d'appareil (`desktop`, `mobile`, `tablet`, `bot`), navigateur, système et **adresse IP masquée**
(`192.168.12.0`). L'adresse IP complète n'est **jamais** stockée.

#### `GET /analytics/summary/`  *(réservé au personnel)*

Nécessite un jeton d'un compte dont **« Statut équipe »** est coché dans l'admin (`401` sans jeton, `403` sinon).

| Paramètre | Défaut | Description |
|---|---|---|
| `days` | `30` | Période analysée (jours) |

```json
{
  "period_days": 30,
  "total_visits": 1284,
  "unique_visitors": 412,
  "by_country":   [ { "country_code": "CA", "count": 980 } ],
  "by_city":      [ { "city": "Montréal", "country_code": "CA", "count": 640 } ],
  "by_device":    [ { "device_type": "mobile", "count": 701 } ],
  "by_browser":   [ { "browser": "Chrome", "count": 800 } ],
  "by_os":        [ { "os": "Android", "count": 520 } ],
  "by_language":  [ { "language": "fr-CA", "count": 900 } ],
  "by_timezone":  [ { "timezone": "America/Toronto", "count": 950 } ],
  "top_pages":    [ { "path": "/", "count": 600 } ],
  "top_referrers":[ { "referrer": "https://google.com/", "count": 120 } ],
  "per_day":      [ { "day": "2026-09-30", "count": 41 } ]
}
```

Chaque liste « top » est limitée à 10 entrées, triée par `count` décroissant.

#### `GET /analytics/visits/`  *(réservé au personnel)*

Visites détaillées, **paginées** (`page`, `page_size` : 50 par défaut, 200 max), de la plus récente à la plus ancienne.

```json
{ "count": 1284, "next": "…?page=2", "previous": null, "results": [
  { "id": 90, "visitor_id": "6f1c…", "path": "/projets", "referrer": "", "language": "fr-CA",
    "timezone": "America/Toronto", "screen_width": 1920, "screen_height": 1080,
    "country": "Canada", "country_code": "CA", "region": "Québec", "city": "Montréal",
    "ip_masked": "192.168.12.0", "device_type": "desktop", "browser": "Chrome", "os": "Windows",
    "created_at": "2026-09-30T20:41:07.120Z" } ] }
```

---

## 5. Les actions

### 5.1 Actions du visiteur (front-end)

| Action | Appel | Résultat |
|---|---|---|
| Voir les prochains évènements | `GET /events/upcoming/?kind=event&limit=4` | Cartes de l'accueil |
| Voir l'activité par onglet | `GET /events/?kind=workshop` (ou `/events/overview/`) | Onglets Évènements / Ateliers / Formations / Compétitions |
| **S'inscrire à une activité** | `POST /registrations/ {event: id, full_name, email}` | Inscription `pending` |
| **S'inscrire à un projet** | `POST /registrations/ {project: id, ...}` | Inscription `pending` (si le projet recrute) |
| **S'inscrire au club** | `POST /registrations/ {full_name, email}` | Demande d'adhésion `pending` |
| Filtrer les projets par catégorie | `GET /projects/?category=web` | Onglets de la page Projets |
| Rechercher un projet | `GET /projects/?search=django` | Barre de recherche |
| Parcourir la bibliothèque | `GET /library/?page=1&page_size=6` | Galerie ; « Voir plus » = page suivante |
| **Envoyer un message** | `POST /contact/` | Message visible dans l'admin |
| Être comptabilisé dans les stats | `POST /analytics/track/` (si consentement) | Une visite enregistrée |

Parcours d'inscription recommandé :

1. L'utilisateur clique sur **S'inscrire** → ouvrez un formulaire (nom, courriel, téléphone facultatif).
2. Envoyez `POST /registrations/`.
3. `201` → affichez « Inscription reçue, vous serez contacté pour confirmation ».
4. `400` → affichez le message du champ concerné (voir le tableau de [4.9](#49-inscriptions)). Masquez le bouton si
   `registration_open` est `false` ou `spots_left` vaut `0`.

### 5.2 Actions du membre connecté

| Action | Appel |
|---|---|
| Se connecter | `POST /auth/login/` |
| Consulter son profil | `GET /auth/me/` |
| Modifier sa présentation, sa photo, ses compétences, ses liens | `PATCH /auth/me/` |
| Consulter les analytics (si « Statut équipe ») | `GET /analytics/summary/`, `GET /analytics/visits/` |

### 5.3 Actions de l'administrateur (interface `/admin/`)

Connexion : `http://localhost:8000/admin/` avec un compte « Statut équipe » (le super-utilisateur voit tout).

#### Modèles et opérations

| Menu admin | Ce que vous pouvez faire |
|---|---|
| **Évènements** | Créer / modifier / supprimer ; filtrer par type, catégorie, date, inscriptions ouvertes ; rechercher par nom, titre ou salle ; voir l'état (À venir, En cours, Terminé, À confirmer) et le nombre d'inscrits |
| **Catégories** | Créer les catégories d'évènements et choisir leur icône Lucide |
| **Catégories de projets** | Créer Web, Mobile, IA / Data… avec icône et ordre |
| **Technologies** | Créer les technologies et leur icône |
| **Projets** | Créer un projet (image sombre, catégorie, technologies, membres, participants, statut, recrutement) ; avertissement si l'image est trop claire |
| **Équipe** | Lier un compte à une photo, un rôle, une présentation, des compétences, des liens ; régler l'ordre et la visibilité (modifiables directement dans la liste) |
| **Bibliothèque** | Ajouter images et vidéos avec légende ; le type est détecté automatiquement |
| **Partenaires** | Ajouter / désactiver des partenaires (compte dans les statistiques) |
| **Réglages du club** | Saisir le nombre de membres actifs, les textes « À propos » et « Mission », les coordonnées de contact (une seule fiche) |
| **Blocs de contenu** | Gérer les valeurs, « Pourquoi participer ? » et le bandeau d'atouts : titre, description, icône, ordre, visibilité |
| **Inscriptions** | Consulter, filtrer, **confirmer**, **annuler**, **exporter en CSV** |
| **Messages de contact** | Lire les messages et cocher « Lu » depuis la liste |
| **Visites** | Consulter les visites collectées (lecture seule) |

#### Actions groupées sur les inscriptions

Dans **Inscriptions**, cochez des lignes puis choisissez dans le menu « Action » :

| Action | Effet |
|---|---|
| **Confirmer les inscriptions sélectionnées** | Statut → `confirmed` |
| **Annuler les inscriptions sélectionnées** | Statut → `cancelled` (la place est libérée dans `spots_left`) |
| **Exporter en CSV** | Télécharge `inscriptions.csv` (nom, courriel, téléphone, cible, statut, date, message) |

#### Procédures pas à pas

**Publier un évènement**
1. Admin → Évènements → *Ajouter*.
2. Choisir le **type**, saisir le **nom**, le **titre** (≤ 20 car.), la **description** (≤ 100 car.), l'image et les catégories.
3. Renseigner date, heures et salle. **Laisser vide ce qui n'est pas décidé** : le front affichera « à confirmer ».
4. Pour une formation sur plusieurs jours : renseigner aussi « Date de fin ».
5. Fixer les places (vide = non précisé) et laisser « Inscriptions ouvertes » coché.
6. Enregistrer : l'évènement est immédiatement servi par l'API.

**Ajouter un projet**
1. Admin → Projets → *Ajouter*.
2. Choisir une image **sombre**, un titre, une description, une catégorie, la date.
3. Sélectionner les technologies et les membres ; indiquer les autres participants (noms séparés par des virgules).
4. « Taille de l'équipe » : laisser vide pour le calcul automatique.
5. Cocher « Recherche des participants » pour ouvrir les inscriptions au projet.

**Créer un membre de l'équipe (avec compte de connexion)**
1. Admin → Authentification → Utilisateurs → *Ajouter* : identifiant, mot de passe, puis prénom et nom.
2. Admin → Équipe → *Ajouter* : choisir cet utilisateur, ajouter photo, rôle, présentation, compétences, liens, ordre.
3. Communiquer l'identifiant au membre : il pourra modifier son profil via `/auth/me/`.
4. Pour qu'il consulte aussi les analytics : cocher « Statut équipe » sur son compte.

**Ajouter à la bibliothèque**
1. Admin → Bibliothèque → *Ajouter* : choisir le fichier, écrire la légende, (miniature pour une vidéo), date facultative.

**Traiter les inscriptions**
1. Admin → Inscriptions → filtrer par évènement (ou statut « En attente »).
2. Sélectionner → *Confirmer* ou *Annuler* ; au besoin *Exporter en CSV* pour contacter les inscrits.

**Mettre à jour les chiffres de l'accueil**
- Membres actifs : Réglages du club. Projets réalisés : statut « Terminé » des projets. Évènements/an : calculé. Partenaires : liste des partenaires actifs.

#### Actions de l'API selon le rôle

| | Visiteur | Membre connecté | Personnel (`is_staff`) |
|---|:-:|:-:|:-:|
| Lire contenus publics | ✅ | ✅ | ✅ |
| S'inscrire / contacter / tracker | ✅ | ✅ | ✅ |
| Modifier son profil | – | ✅ | ✅ |
| Lire les analytics | – | – | ✅ |
| Créer / modifier le contenu | – | – | via `/admin/` |

---

## 6. Règles de saisie

### Évènement
| Champ | Règle |
|---|---|
| Type | `Évènement`, `Atelier`, `Formation`, `Compétition` |
| Nom | obligatoire, 150 car. |
| Titre | obligatoire, **20 car. max** |
| Description | obligatoire, **100 car. max** |
| Date / heures / salle / places | facultatifs (vide = « à confirmer ») |
| Date de fin | ≥ date de début |
| Heure de fin | après l'heure de début (si même jour) |
| Image | facultative |

### Projet
| Champ | Règle |
|---|---|
| Image | obligatoire, **sombre de préférence** (avertissement dans l'admin si luminosité > 110/255) |
| Titre | obligatoire, 100 car. |
| Description | obligatoire |
| Catégorie | facultative (liste de l'admin) |
| Technologies / membres | facultatifs, choix multiples |
| Autres participants | noms séparés par des virgules (255 car.) |
| Date | obligatoire |

### Membre de l'équipe
Compte lié obligatoire (un compte = un profil). Photo, présentation, compétences, courriel public, liens : facultatifs.

### Bibliothèque
Extensions autorisées : `jpg jpeg png webp gif avif mp4 webm mov m4v`. Légende obligatoire (200 car.).
Taille maximale d'envoi par défaut : 5 Mo (voir `FILE_UPLOAD_MAX_MEMORY_SIZE` dans `settings.py` ; à relever pour les vidéos).

---

## 7. Correspondance pages du front → API

| Page / bloc | Appel |
|---|---|
| Accueil – Prochains évènements | `GET /events/upcoming/?kind=event&limit=4` |
| Accueil – À propos | `GET /site/` → `about` |
| Accueil – 4 chiffres | `GET /stats/` |
| Accueil – Projets récents | `GET /projects/recent/?limit=4` |
| Accueil – « S'inscrire au club » | `POST /registrations/` (sans cible) |
| Le club – Mission / Valeurs | `GET /site/` → `mission`, `values` |
| Le club – Équipe | `GET /team/` |
| Le club – Bibliothèque | `GET /library/?page_size=6` puis `?page=2` |
| Activités – Onglets | `GET /events/?kind=…` ou `GET /events/overview/` |
| Activités – « S'inscrire » | `POST /registrations/ {event}` |
| Activités – Pourquoi participer / bandeau | `GET /site/` → `why_participate`, `perks` |
| Projets – Onglets de catégories | `GET /project-categories/` |
| Projets – Liste + recherche | `GET /projects/?category=&search=` |
| Projets – En chiffres | `GET /projects/summary/` |
| Projets – Technologies utilisées | `GET /technologies/` |
| Bouton « Nous contacter » | `POST /contact/` |
| Toutes les pages | `POST /analytics/track/` (si consentement) |

---

## 8. Exemples de code front-end

### Client minimal (`api.js`)

```js
const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

export async function api(path, { method = "GET", body, token } = {}) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      ...(body && !(body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Token ${token}` } : {}),
    },
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw Object.assign(new Error("API error"), { status: res.status, data });
  return data;
}

// Utilisation
const events = await api("/events/upcoming/?kind=event&limit=4");
const stats = await api("/stats/");
```

### Icône Lucide à partir de la réponse

```jsx
import * as Icons from "lucide-react";

export function ApiIcon({ icon, size = 20, ...props }) {
  const Icon = icon && Icons[icon.component];
  return Icon ? <Icon size={size} {...props} /> : null;
}

// <ApiIcon icon={event.icon} />   <ApiIcon icon={stats.partners.icon} />
```

### Afficher « à confirmer » et formater

```js
const hhmm = (t) => t?.slice(0, 5);                         // "14:30:00" -> "14:30"

export function eventInfo(e) {
  return {
    date: e.date ? new Date(e.date).toLocaleDateString("fr-CA") : "Date à confirmer",
    time: e.start_time ? `${hhmm(e.start_time)} - ${hhmm(e.end_time)}` : "Horaire à confirmer",
    room: e.room || "Lieu à confirmer",
    seats: e.spots_left != null ? `${e.spots_left} places restantes`
         : e.capacity != null ? `${e.capacity} places` : "Places à confirmer",
    canRegister: e.registration_open && e.status !== "finished" && e.spots_left !== 0,
  };
}

// Projets : "Mai 2025" et "Équipe de 4"
const monthYear = (d) => new Date(d).toLocaleDateString("fr-CA", { month: "long", year: "numeric" });
```

### Inscription

```js
async function register(eventId, form) {
  try {
    await api("/registrations/", { method: "POST", body: { event: eventId, ...form } });
    return { ok: true };
  } catch (e) {
    if (e.status === 429) return { ok: false, message: "Trop de tentatives, réessayez plus tard." };
    const first = Object.values(e.data ?? {}).flat()[0];     // 1er message d'erreur
    return { ok: false, message: first ?? "Erreur inattendue." };
  }
}
// Adhésion au club : api("/registrations/", { method: "POST", body: { full_name, email } })
```

### Bibliothèque avec « Voir plus »

```js
let next = `/library/?page_size=6`;
async function loadMore() {
  if (!next) return [];
  const page = await api(next.replace(API, ""));   // `next` est une URL absolue
  next = page.next;
  return page.results;
}
```

### Connexion et mise à jour du profil

```js
const { token } = await api("/auth/login/", { method: "POST", body: { username, password } });
const me = await api("/auth/me/", { token });

const fd = new FormData();
fd.append("bio", "Ma nouvelle présentation");
fd.append("photo", fileInput.files[0]);
await api("/auth/me/", { method: "PATCH", body: fd, token });
```

### Tracking avec consentement

```js
export function track() {
  if (localStorage.getItem("analytics-consent") !== "yes") return;   // bannière de consentement
  const vid = localStorage.getItem("vid") ?? (localStorage.vid = crypto.randomUUID());
  api("/analytics/track/", {
    method: "POST",
    body: {
      visitor_id: vid,
      path: location.pathname,
      referrer: document.referrer,
      language: navigator.language,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      screen_width: screen.width,
      screen_height: screen.height,
      consent: true,
    },
  }).catch(() => {});
}
// Appelez track() à chaque changement de route.
```

---

## 9. Configuration et déploiement

### Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `DJANGO_SECRET_KEY` | clé de dev | **À définir en production** |
| `DJANGO_DEBUG` | `1` | Mettre `0` en production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Domaines autorisés (séparés par des virgules) |
| `DJANGO_CORS_ORIGINS` | `localhost:5173,127.0.0.1:5173,localhost:3000` | Adresses du front |
| `DJANGO_TIME_ZONE` | `America/Toronto` | Fuseau des dates/heures d'évènements |
| `GEOIP_DB_PATH` | vide | Chemin de `GeoLite2-City.mmdb` (ville/région) ; nécessite `pip install geoip2` |
| `TRUST_X_FORWARDED_FOR` | `0` | `1` seulement derrière un proxy de confiance (nginx, Cloudflare) |

### Liste de contrôle avant la mise en ligne

- [ ] `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` défini, `DJANGO_ALLOWED_HOSTS` renseigné
- [ ] `DJANGO_CORS_ORIGINS` = adresse réelle du front (en `https://`)
- [ ] Les fichiers `/media/` sont servis par le serveur web (nginx…) : Django ne les sert qu'en `DEBUG`
- [ ] Les fichiers statiques de l'admin sont collectés (`collectstatic`) et servis
- [ ] Base de données de production (PostgreSQL recommandé à la place de SQLite) et sauvegardes
- [ ] HTTPS activé ; `TRUST_X_FORWARDED_FOR=1` uniquement si le proxy écrase l'en-tête `X-Forwarded-For`
- [ ] Limite d'envoi relevée si vous déposez des vidéos (et `client_max_body_size` côté nginx)
- [ ] Bannière de consentement et politique de confidentialité en place avant d'activer le tracking

### Structure du code

| Fichier | Contenu |
|---|---|
| `club/models.py` | Modèles (évènements, projets, équipe, bibliothèque, inscriptions, visites…) |
| `club/serializers.py` | Format JSON des réponses |
| `club/views.py` | Endpoints |
| `club/urls.py` | Routes de `/api/` |
| `club/admin.py` | Interface d'administration et actions groupées |
| `club/icons.py` | Liste des icônes Lucide disponibles |
| `club/utils.py` | Arrondi « 150+ », géolocalisation, analyse du navigateur |
| `club/management/commands/seed_demo.py` | Données d'exemple |

---

## 10. Vie privée et analytics

- Le tracking **ne s'exécute qu'avec consentement** : sans `consent: true`, rien n'est enregistré.
- L'adresse IP **n'est jamais stockée entière** : le dernier octet (IPv4) ou les derniers blocs (IPv6) sont masqués ; l'IP complète sert uniquement, en mémoire, à déterminer le pays/la ville.
- Le `visitor_id` est un identifiant aléatoire généré par le navigateur ; il ne contient aucune donnée personnelle.
- Les données collectées : pages vues, provenance (referrer), langue, fuseau horaire, taille d'écran, appareil, navigateur, système, pays/région/ville.
- L'interrogation des analytics est réservée au personnel.
- Prévoyez une politique de confidentialité conforme à la loi applicable (Loi 25 au Québec, RGPD en Europe) et un moyen de retirer son consentement (supprimer `analytics-consent` côté front).

---

## 11. Aide-mémoire

```text
ÉVÈNEMENTS     GET  /events/                   ?kind= &category= &status= &limit=
               GET  /events/recent/            ?limit= &kind=
               GET  /events/upcoming/          ?limit= &kind=
               GET  /events/overview/          ?limit= &recent_days=
               GET  /events/by-category/       ?kind= &limit=
               GET  /categories/
PROJETS        GET  /projects/                 ?category= &technology= &search= &limit=
               GET  /projects/recent/          ?limit=
               GET  /projects/summary/
               GET  /project-categories/
               GET  /technologies/
CLUB           GET  /team/        GET /library/ ?type= &page= &page_size=
               GET  /stats/       GET /site/    GET /partners/
ACTIONS        POST /registrations/            {event|project|rien, full_name, email, phone?, message?}
               POST /contact/                  {name, email, subject?, message}
COMPTE         POST /auth/login/               {username, password}
               GET|PATCH /auth/me/             Authorization: Token …
ANALYTICS      POST /analytics/track/          {visitor_id, path, consent, …}
               GET  /analytics/summary/        ?days=   (personnel)
               GET  /analytics/visits/         ?page=   (personnel)
```
