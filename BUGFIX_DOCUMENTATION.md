# Bugfix-Dokumentation AdventureLog

## Bug #888: PATCH Location with visits fails

**Datum:** 2026-02-09
**Symptom:** TypeError: "Direct assignment to the reverse side of a related set is prohibited."
**Ursache:** `LocationSerializer.update()` hat `visits` nicht aus `validated_data` extrahiert, bevor die `setattr`-Schleife lief.

### Geaenderte Datei

**`backend/server/adventures/serializers.py`** - Methode `LocationSerializer.update()` (ab Zeile 437)

### Aenderungen

1. `has_visits = "visits" in validated_data` entfernt (nicht mehr noetig)
2. `visits_data = validated_data.pop("visits", None)` hinzugefuegt - extrahiert visits VOR der setattr-Schleife
3. Nach `instance.save()` wird die Visit-Relation korrekt behandelt:
   - Alte Visits loeschen: `instance.visits.all().delete()`
   - Neue Visits erstellen: `Visit.objects.create(location=instance, **visit_data)`

Das Pattern ist konsistent mit der Behandlung von `category` und `collections` in derselben Methode.

---

## Bug #991: Wikipedia/URL Image Upload fails - "Failed to fetch image"

**Datum:** 2026-02-09
**Symptom:** Upload von Bildern aus Wikipedia oder externen URLs scheitert mit "Error fetching image from Wikipedia".
**Ursache:** Drei zusammenhaengende Probleme:

### Problem 1: CORS-Blockade (Hauptursache)

Das Frontend versuchte, Bilder direkt von externen URLs (z.B. upload.wikimedia.org) per fetch() herunterzuladen. Browser blockieren dies wegen Cross-Origin-Restrictions.

### Problem 2: Session-Cookie wird nicht weitergeleitet

Der SvelteKit-API-Proxy (frontend/src/routes/api/[...path]/+server.ts, Zeile 74) ueberschreibt den Cookie-Header mit nur dem CSRF-Token und verliert dabei das sessionid-Cookie. Dadurch sieht Django einen anonymen Benutzer. ContentImagePermission.has_permission() blockiert anonyme POST-Requests mit 403 Forbidden.

### Problem 3: SvelteKit Body-Size-Limit

Das Standard-Limit von adapter-node ist 512 KB. Wikipedia-Bilder ueberschreiten dies oft deutlich (2-12 MB), was zu 500 Internal Server Error fuehrt.

---

### Alle geaenderten Dateien

#### 1. Backend: backend/server/adventures/views/location_image_view.py

Neuer Endpoint `fetch_from_url` im ContentImageViewSet:

- Route: POST /api/images/fetch_from_url/
- Permission: AllowAny (noetig weil SvelteKit-Proxy sessionid nicht weiterleitet)
- Funktion: Laedt Bilder serverseitig herunter, gibt rohe Bytes mit korrektem Content-Type zurueck
- Sicherheitsmassnahmen:
  - URL-Schema-Validierung (nur http/https)
  - SSRF-Schutz: Blockiert private/interne IPs (localhost, 192.168.x.x, 10.x.x.x etc.)
  - Content-Type-Pruefung (nur image/* erlaubt)
  - Groessenlimit: 20 MB
  - Timeout: 30 Sekunden
  - Custom User-Agent gegen Rate-Limiting

Neue Imports: AllowAny, HttpResponse, ipaddress, urlparse

#### 2. Frontend: frontend/src/lib/components/ImageManagement.svelte

Funktion fetchImageFromUrl() (Zeile 134) umgestellt von direktem fetch(imageUrl) auf den Backend-Proxy:

    fetch("/api/images/fetch_from_url/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: imageUrl })
    });

Behebt sowohl "Upload from URL" als auch Wikipedia-Bildersuche.

#### 3. Backend: backend/server/requirements.txt

requests>=2.31.0 hinzugefuegt (war bereits genutzt, fehlte aber in der Deklaration).

#### 4. Environment: .env

    BODY_SIZE_LIMIT=Infinity

Erhoeht das SvelteKit adapter-node Body-Size-Limit (wie in .env.example empfohlen).

---

### Warum AllowAny statt IsAuthenticated?

Der SvelteKit-API-Proxy ueberschreibt den Cookie-Header (Zeile 74 in +server.ts):

    Cookie: csrftoken=${csrfToken}; Path=/; HttpOnly; SameSite=Lax

Dadurch geht das sessionid-Cookie verloren. Fuer fetch_from_url (detail=False) gibt es kein Content-Objekt, daher brauchen wir AllowAny. Der Endpoint ist durch SSRF-Schutz, Content-Type-Validierung und Groessenlimits abgesichert.

Langfristige Empfehlung: Den SvelteKit-Proxy fixen, damit er sessionid im Cookie mitsendet. Dann koennte AllowAny durch die Standard-Permission ersetzt werden.

### Deployment-Hinweise

- Quelldateien auf dem Host sind dauerhaft geaendert
- Bei docker-compose build werden die Aenderungen in neue Images uebernommen
- Der kompilierte Frontend-Build wurde im laufenden Container gepatcht - geht bei Container-Neuerstellung verloren und muss durch docker-compose build ersetzt werden
- BODY_SIZE_LIMIT=Infinity ist in .env persistent


---

## Bug: Location-Erstellung schlaegt fehl + Wikipedia-Bilder kaputt angezeigt

**Datum:** 2026-02-10
**Symptom:** Locations koennen nicht gespeichert werden (kein Feedback). Wikipedia-Bilder werden als kaputte Platzhalter angezeigt ("Uploaded content" ohne Bild).
**Ursache:** Drei zusammenhaengende Probleme im Frontend.

### Problem 1: Fehlender addToast-Import in LocationDetails.svelte

`addToast()` wurde in der Fehlerbehandlung von `handleSave()` aufgerufen, war aber nicht importiert. Dadurch:
- Bei einem Backend-Fehler (z.B. 400 Bad Request) crashte die Funktion mit ReferenceError
- Der Benutzer bekam keinerlei Feedback, warum das Speichern fehlschlug
- Die `save`-Event-Dispatch wurde nie erreicht, der Modal blieb im "Details"-Schritt haengen

**Fix:** Import hinzugefuegt:

    import { addToast } from '$lib/toasts';

### Problem 2: Fehlende Fehlerbehandlung bei Bild-Uploads (ImageManagement.svelte)

Die Funktion `uploadImageToServer()` pruefte die Server-Response nicht auf Fehler:
- Wenn der Backend-Bildupload fehlschlug, gab die SvelteKit-Action `{ error: "..." }` zurueck
- Der Client-Code ignorierte das `error`-Feld und erstellte ein Bild-Objekt mit `id: undefined, image: undefined`
- Diese "Geister-Bilder" erschienen als kaputte Platzhalter in der "Current Images"-Galerie

**Fix:** Zwei zusaetzliche Pruefungen nach dem Deserialisieren:

    if (newData.data && newData.data.error) {
        addToast('error', String(newData.data.error));
        return null;
    }
    if (!newData.data || !newData.data.id || !newData.data.image) {
        addToast('error', 'Image upload failed - incomplete response');
        return null;
    }

### Problem 3: Server-Action gibt HTML statt JSON zurueck (+page.server.ts)

Die `image`-Action in `/locations/+page.server.ts` rief `res.json()` auf, ohne zu pruefen ob die Backend-Antwort tatsaechlich JSON war. Bei Backend-Fehlern (HTML-Fehlerseite) crashte die Action mit `SyntaxError: Unexpected token '<'`.

**Fix:** Content-Type-Pruefung vor dem JSON-Parsing:

    const contentType = res.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
        console.error(`Image upload failed with status ${res.status}:`, text.substring(0, 200));
        return { error: `Image upload failed (status ${res.status})` };
    }

### Alle geaenderten Dateien

| Datei | Aenderung |
|-------|-----------|
| `frontend/src/lib/components/locations/LocationDetails.svelte` | `addToast`-Import hinzugefuegt, Fehlerbehandlung bei `!res.ok` |
| `frontend/src/lib/components/ImageManagement.svelte` | `objectId`-Pruefung, Error-Response-Handling nach Upload |
| `frontend/src/routes/locations/+page.server.ts` | Content-Type-Pruefung in der `image`-Action |

---

## Bug: Ungueltige URLs im Link-Feld verhindern Location-Speicherung

**Datum:** 2026-02-10
**Symptom:** Wenn im "Link"-Feld ein ungueltiger Wert eingegeben wird (z.B. "dddd"), kann der Standort nicht gespeichert werden. Django gibt `400 Bad Request` mit `{"link": ["Enter a valid URL."]}` zurueck.
**Ursache:** Django's `URLField`-Validator lehnt ungueltige URLs ab. Das Frontend sendete den Wert unvalidiert und zeigte nur "Failed to save location" als generische Fehlermeldung.

### Fix 1: URL-Validierung im Frontend (LocationDetails.svelte)

Vor dem Senden des Payloads wird das Link-Feld bereinigt:

    if (!payload.link || !payload.link.trim()) {
        payload.link = null;
    } else {
        try {
            new URL(payload.link);
        } catch {
            payload.link = null;  // Ungueltige URL → null
        }
    }

Leere Strings, Whitespace und ungueltige URLs werden zu `null` konvertiert, damit Django sie akzeptiert. Gleiches gilt fuer leere `description`-Felder.

### Fix 2: Bessere Fehlermeldungen fuer Django-Feld-Fehler

Die Error-Extraktion wurde erweitert, um Django's Feld-Fehler-Format zu unterstuetzen:

    const fieldErrors = Object.entries(errorData)
        .filter(([_, v]) => Array.isArray(v))
        .map(([k, v]) => `${k}: ${v.join(', ')}`)
        .join('; ');
    errorMsg = fieldErrors || 'Failed to save location';

Statt nur `detail` und `name` zu pruefen, werden jetzt alle Feld-Fehler extrahiert und als Toast angezeigt (z.B. "link: Enter a valid URL.").

### Geaenderte Datei

| Datei | Aenderung |
|-------|-----------|
| `frontend/src/lib/components/locations/LocationDetails.svelte` | URL-Validierung + verbesserte Fehlerausgabe |

### Deployment-Hinweis

Frontend wurde im Container neu gebaut (`pnpm run build`) und der Container neu gestartet. Bei Container-Neuerstellung muss erneut gebaut werden oder ein neues Image erstellt werden.
