# Einsatzleitsoftware

BFF für die Einsatzleitung auf Basis von Django, Django REST Framework,
PostgreSQL und Django Channels mit Redis.

## Entwicklung im Dev Container

Das Projekt in VS Code über **Reopen in Container** öffnen. Der Dev Container
startet die Django-Anwendung automatisch auf <http://localhost:8000> und stellt
PostgreSQL sowie Redis als Compose-Services bereit.

Alternativ kann der Stack auch direkt gestartet werden:

```bash
docker compose up
```

Migrationen werden innerhalb des App-Containers ausgeführt:

```bash
docker compose exec app python manage.py migrate
```

Die Zugangsdaten und Hostnamen sind ausschließlich für die lokale Entwicklung
gedacht und stehen in `docker-compose.yml`.

## Produktionscontainer

Der mehrstufige Build erstellt ein Django/Channels-Image und ein Nginx-Image
mit dem gebauten Vue-Frontend. Für einen lokalen Produktionslauf `.env.example`
nach `.env` kopieren, beide Pflichtgeheimnisse ersetzen und den Stack starten:

```bash
cp .env.example .env
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml exec app python manage.py migrate
```

Die Anwendung ist anschließend unter <http://localhost:8080> erreichbar. Für
einen echten Internetbetrieb müssen `DJANGO_ALLOWED_HOSTS` und
`DJANGO_CSRF_TRUSTED_ORIGINS` zur Domain passen und HTTPS an einem vertrauenswürdigen
Reverse Proxy terminiert werden. Dort zusätzlich `DJANGO_SECURE_COOKIES` und
`DJANGO_SECURE_SSL_REDIRECT` auf `true` setzen. Die Datenbank und Redis liegen
auf persistenten Compose-Volumes; `.env` enthält Geheimnisse und darf nicht
committet werden.

## GitHub Build

Der Workflow in `.github/workflows/build.yml` führt bei Pull Requests und
Änderungen auf `main` Django-Tests, Frontend-Build und Kartenkalibrierungstests
aus und baut beide Docker-Ziele. Er veröffentlicht Images nicht automatisch.


## Frontend

Das Vue-Frontend läuft mit dem Compose-Stack auf <http://localhost:5173>. Es verwendet
die Django-Session-Authentifizierung und leitet API-Anfragen im Dev-Server an Port 8000 weiter.

Ein Benutzer kann zunächst über die Django-Administration angelegt werden. Zum Erstellen
eines Einsatzes benötigt er die Berechtigung `missions.add_mission`.

### Keycloak-SSO

Keycloak-SSO ist optional. In `.env` müssen `KEYCLOAK_SERVER_URL` (Basis-URL),
`KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET` und
`KEYCLOAK_REQUIRED_GROUP` gesetzt werden. Die Gruppenprüfung vergleicht den
Gruppennamen exakt mit dem Claim `groups`; die Claim-Bezeichnung kann über
`KEYCLOAK_GROUPS_CLAIM` angepasst werden. Die Anmeldung fordert standardmäßig
`openid email profile groups` an. Der optionale Keycloak-Client-Scope `groups`
muss existieren und dem Client zugewiesen sein; bei abweichendem Scope-Namen
`KEYCLOAK_GROUPS_SCOPE` entsprechend setzen. Der Group-Membership-Mapper muss
den Gruppen-Claim in die
UserInfo-Antwort oder den ID-Token aufnehmen. Als
Redirect-URI des Clients `https://<domain>/oidc/callback/` eintragen.
Als **Valid post logout redirect URIs** zusätzlich `https://<domain>/` eintragen
(inklusive abschließendem Slash; lokal die tatsächliche Origin mit Port verwenden).
Der Abmelde-Button sendet immer einen CSRF-geschützten Formular-POST an
`/api/auth/logout/`. Ohne SSO beendet die OIDC-View die lokale Sitzung und leitet
zur Startseite weiter. Mit SSO erzeugt sie die Keycloak-Logout-URL mit `id_token_hint`,
beendet die Django-Sitzung und leitet den Browser zu Keycloak und anschließend
zur Startseite zurück. ID-Tokens werden dafür serverseitig in der Sitzung gespeichert.
Bei bestehenden Sitzungen ohne gespeicherten ID-Token kann Keycloak eine
Abmeldebestätigung anzeigen; nach erneuter Anmeldung steht der Token zur Verfügung.

Beim erfolgreichen ersten SSO-Login wird ein Konto automatisch angelegt, wenn
der konfigurierte Gruppen-Claim die erforderliche Gruppe enthält. Das Konto
wird aktiv angelegt; Vor- und Nachname werden aus den OIDC-Claims übernommen.
Benutzer ohne passende Gruppe werden vor der Registrierung abgewiesen.
Ohne vollständige Keycloak-Konfiguration bleibt SSO deaktiviert.

### Benutzerrechte

Nach `migrate` erhalten alle bestehenden und neu angelegten Konten die Django-
Gruppe `Standardbenutzer`. Sie erhält die Modellrechte für die operativen Apps
Karte, Verwaltung, Einsätze, Patienten und Teams. Lese-, Anlege- und
Änderungsrechte erlauben den normalen Betrieb; Löschrechte bleiben bewusst
Administratoren vorbehalten. Die Gruppe verleiht weder Staff- noch
Superuserstatus und enthält keine Rechte zur Benutzerverwaltung. Die API prüft
Rechte serverseitig; die Oberfläche blendet nicht erlaubte Aktionen aus und
zeigt fehlende Rechte verständlich an.

### Frontend-Struktur

`frontend/src/layouts/BaseLayout.vue` ist das gemeinsame Basis-Template. Es enthält
Seitenrahmen, Logo, Kopfbereich und Navigation für Login, Einsatzauswahl und den
aktiven Einsatz. Der Inhalt der jeweiligen Unterseite wird über den Standard-Slot
(`<slot />`) eingesetzt.

`frontend/src/App.vue` steuert Anmeldestatus und Seitenwahl und setzt die passende
Komponente aus `frontend/src/views/` in das Layout ein. Die Views enthalten nur
Seiteninhalt und die zugehörige Logik; sie binden keine anderen Unterseiten ein.
Neue Einsatzseiten werden in `App.vue` eingebunden und in der Navigation von
`BaseLayout.vue` ergänzt.


### Kartenmodul

Unter **Karte** wird je Einsatz ein gespeichertes Geländeoverlay angezeigt.
Angemeldete Benutzer können die Karte lesen; Benutzer mit Django-Staffstatus
(`is_staff`) erhalten den **Adminmodus** und dürfen die Konfiguration speichern.

Im Adminmodus SVG, PNG, JPEG, GIF oder WebP (maximal 1 MB) auswählen.
Über **Stützpunkt hinzufügen** beliebig viele Zuordnungen anlegen: ausgewählten
Punkt frei im Bild und anschließend an der entsprechenden Position auf der Karte
anklicken. Alternativ Bildkoordinaten (0/0 oben links, 1/1 unten rechts) und
Breiten-/Längengrad eingeben. Kartenmarker sind verschiebbar, Punkte entfernbar.

- Ohne Punkte bleibt die aktuelle Platzierung erhalten; neue Bilder erscheinen
  zunächst im aktuellen Kartenausschnitt.
- Ein Punkt verschiebt die Grafik bei unveränderter Größe und Drehung.
- Zwei Punkte drehen und skalieren die bisherige Platzierung gleichmäßig.
- Drei nicht kollineare Bildpunkte bestimmen eine affine Transformation.
- Mehr Punkte werden gemeinsam mittels kleinster Quadrate affin ausgeglichen.
  Die angenäherte Abweichung je Punkt wird in Metern angezeigt; dies ist keine
  lokale Verformung der Grafik.

Die Deckkraft ist anpassbar; **Abbrechen** verwirft den Entwurf. **Speichern**
persistiert Bild, alle Stützpunkte, berechnete Ecken und Deckkraft je Einsatz.
SVG wird ausschließlich als Bild angezeigt, nicht als HTML eingebettet.
Die OpenStreetMap-Hintergrundkarte benötigt Internetzugang.

**Stützpunkte exportieren** liefert `overlay_points.json` mit `control_points`
(Einträge mit `x`, `y`, `lat`, `lng`) und den berechneten `corners`. Der Import
unterstützt dieses Format sowie bisherige `overlay_corners.json`-Dateien:

```json
{
  "topLeft": {"lat": 52.52, "lng": 13.40},
  "topRight": {"lat": 52.52, "lng": 13.41},
  "bottomLeft": {"lat": 52.51, "lng": 13.40}
}
```

**Ecken exportieren** liefert weiterhin dieses Leaflet-kompatible Format.
Bereits gespeicherte Overlays werden mit ihren drei Eckpunkten weiterbearbeitet.
Die Berechnung lässt sich mit `node --test src/map/calibration.test.js` im
Frontend-Verzeichnis prüfen.

Die Ausrichtung erfolgt mit Leaflet und `leaflet-imageoverlay-rotated`.
Die API liegt unter `/api/missions/<id>/map/` (GET, PUT).
Nach Aktualisierung `npm ci` im Frontend und `python manage.py migrate` im
Backend ausführen; die Nginx-Konfiguration erlaubt den Upload inklusive
Base64-Overhead bis 2 MB.

**GeoJSON importieren** im Adminmodus fügt `.geojson`- oder `.json`-Dateien hinzu
(maximal 1 MB / 50.000 Koordinaten je Datei). Jeder Import wird sofort separat
für den Einsatz gespeichert und beim Öffnen der Karte wieder geladen; ein
Bildoverlay ist nicht erforderlich. Weitere Imports ergänzen die vorhandenen
Daten. Die Dateien werden ausschließlich importiert, nicht auf der Karte editiert.

Unterstützt werden FeatureCollection, Feature und die GeoJSON-Geometrietypen mit
WGS84-Koordinaten `[Längengrad, Breitengrad]`. Linien (auch MultiLineString) und
Features mit `properties.type` **RMHP** oder **LZ** werden sichtbar dargestellt.
Die beiden Punkttypen verwenden beschriftete SVG-Symbole aus
`frontend/src/assets/map/`. Die sichtbaren Typen stehen in `SHOW_TYPES` in
`frontend/src/map/geojson.js`.

Linien übernehmen `stroke`/`color`, `stroke-width`/`weight`,
`stroke-opacity`/`opacity`, `dashArray`, `lineCap` und `lineJoin`.
Alle Geometrien mit `popupContent` sind zusätzlich über eine unsichtbare,
vergrößerte Klickfläche erreichbar. Popups unterstützen einfache HTML-Formatierung
und HTTP(S)-Links; aktive Inhalte und Ereignisattribute werden entfernt.
Die API `/api/missions/<id>/map/geojson/` bietet GET für angemeldete Benutzer
und POST für Staff-Benutzer. PUT, PATCH und DELETE sind nicht vorgesehen.


Importierte GeoJSON-Punkte können unter `/admin/map/geojsonimport/` in der
Django-Administration bearbeitet werden: Import auswählen, Längengrad,
Breitengrad, Typ oder Popup ändern und speichern. Point- und MultiPoint-Geometrien
sowie Punkte in GeometryCollections werden unterstützt. Zusätzliche Koordinaten
(z. B. Höhe), weitere Properties und andere Geometrien bleiben erhalten.
Die Kartenansicht übernimmt die Änderungen beim nächsten Laden.
Erforderlich sind Staffstatus und die Django-Berechtigung
`map.change_geojsonimport` (Superuser besitzen diese bereits). Neue Daten werden
weiterhin über den GeoJSON-Import auf der Karte angelegt.


## Installation als PWA

Der Frontend-Produktionsbuild enthält das Web-App-Manifest, App-Icons und einen
Service Worker. Die Anwendung muss über HTTPS (oder lokal über localhost)
erreichbar sein. In Chrome/Edge lässt sie sich über das Installationssymbol bzw.
das Browsermenü installieren. Auf iPhone/iPad in Safari „Teilen“ → „Zum
Home-Bildschirm“ wählen. Die installierte App startet in einem eigenen Fenster.

Ohne Verbindung erscheint beim erneuten Öffnen eine Offline-Hinweisseite.
Einsatz-, Patienten- und API-Daten werden vom Service Worker nicht gespeichert;
für die Arbeit mit aktuellen Daten ist eine Verbindung erforderlich. Im
Vite-Entwicklungsmodus wird kein Service Worker registriert.
