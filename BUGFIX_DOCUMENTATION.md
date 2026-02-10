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


---

## Bug: World Map - Countries Not Visually Highlighted Despite Visit Count

**Datum:** 2026-02-10
**Symptom:** Laender auf der World Map werden nicht farblich hervorgehoben, obwohl Besuche (num_visits > 0) registriert sind. Deutschland zeigt z.B. einen Besuchszaehler, bleibt aber auf der Karte unmarkiert/unsichtbar.
**Ursache:** Die originalen Tailwind-CSS-Klassen (`bg-red-200`, `bg-green-200`, `bg-blue-200`) waren zu pastellfarben/hell, um auf der dunklen Basemap (CARTO Dark Matter) sichtbar zu sein. Die Marker verschmolzen optisch mit dem Kartenhintergrund. Das Backend lieferte korrekte Daten.

### Analyse

1. **Backend (korrekt):** `CountrySerializer.get_num_visits()` in `backend/server/worldtravel/serializers.py` zaehlt `VisitedRegion`-Objekte korrekt. Deutschland hatte `num_visits: 1`.
2. **Frontend-Logik (korrekt):** `getVisitStatusClass()` in `+page.svelte` ordnete den Status korrekt zu: `partial` -> `bg-blue-200`.
3. **Visuelles Problem:** `bg-blue-200` = `rgb(191, 219, 254)` ist ein sehr helles Blau, das auf der dunklen Karte kaum sichtbar ist.

### Fix 1: Laufende Instanz (CSS-Injection via hooks.server)

**Datei:** `/app/build/server/chunks/hooks.server-Brt-kPkC.js` (kompiliert, im Container)

Die `themeHook`-Funktion wurde in beiden Branches (mit und ohne gesetztem Theme) erweitert, um per `transformPageChunk` ein inline `<style>`-Tag in den HTML-`<head>` zu injizieren:

    .replace("</head>", "<style>.bg-blue-200{background-color:oklch(0.72 0.15 230)!important}.bg-green-200{background-color:oklch(0.72 0.15 150)!important}.bg-red-200{background-color:oklch(0.85 0.03 250)!important}</style></head>")

**Farbzuordnung:**
| Status | Klasse | Originalfarbe | Neue Farbe (oklch) | Beschreibung |
|--------|--------|---------------|--------------------|----|
| Partial | `bg-blue-200` | `rgb(191,219,254)` (pastellblau) | `oklch(0.72 0.15 230)` | Kraeftiges Blau |
| Complete | `bg-green-200` | `rgb(187,247,208)` (pastellgruen) | `oklch(0.72 0.15 150)` | Kraeftiges Gruen |
| Not Visited | `bg-red-200` | `rgb(254,202,202)` (pastellrot) | `oklch(0.85 0.03 250)` | Gedaempftes Grau |

**Warum CSS-Injection statt Datei-Patch?**
SvelteKit markiert kompilierte Assets als `Cache-Control: immutable`. Aenderungen an CSS/JS-Dateien werden vom Browser nicht neu geladen. Die serverseitige HTML-Injection umgeht dieses Caching komplett.

### Fix 2: Quellcode (fuer naechsten Build)

**Datei:** `frontend/src/routes/worldtravel/+page.svelte` - Funktion `getVisitStatusClass()`

**Vorher:**

    case "not_visited": return "bg-red-200";
    case "complete":    return "bg-green-200";
    default:            return "bg-blue-200";

**Nachher:**

    case "not_visited": return "bg-red-400";
    case "complete":    return "bg-green-400";
    default:            return "bg-blue-400";

Die `-400`-Varianten sind deutlich kraeftiger als `-200` und auf der dunklen Karte klar sichtbar. Diese Standard-Tailwind-Klassen werden garantiert im naechsten Build in das CSS-Bundle aufgenommen.

### Alle geaenderten Dateien

| Datei | Typ | Aenderung |
|-------|-----|-----------|
| `frontend/src/routes/worldtravel/+page.svelte` | Quellcode (Host) | `bg-*-200` → `bg-*-400` in `getVisitStatusClass()` |
| `/app/build/server/chunks/hooks.server-Brt-kPkC.js` | Kompiliert (Container) | CSS-Injection mit oklch-Farben in `transformPageChunk` |
| `/app/build/client/_app/immutable/assets/0.pYBZ-xsX.css` | Kompiliert (Container) | CSS-Definitionen von `bg-*-200` ueberschrieben |

### Deployment-Hinweis

- Die CSS-Injection im Container wirkt sofort, geht aber bei Container-Neuerstellung verloren.
- Der Quellcode-Fix (`bg-*-400`) greift erst nach einem neuen Frontend-Build (`pnpm run build`).
- Nach dem naechsten Build ist die CSS-Injection nicht mehr noetig, da die `-400`-Klassen von sich aus sichtbar sind.


---

## Bug #617: Cannot Change Adventure from Private to Public

**Datum:** 2026-02-10
**Symptom:** Ein bestehendes privates Adventure (Location) kann nicht auf Public umgestellt werden. Nach dem Speichern bleibt die Location privat. Keine Fehlermeldung in Logs oder UI.
**Ursache:** Race Condition zwischen `instance.save()` und dem `m2m_changed`-Signal bei Collections.

### Analyse

1. **Backend-Serializer (Hauptursache):** In `LocationSerializer.update()` wurde `instance.collections.set()` VOR `instance.save()` aufgerufen. Das `m2m_changed`-Signal (`update_adventure_publicity` in `signals.py`) prueft, ob die Collection `is_public=False` hat, und setzt dann `location.is_public = False`. Da `instance.save()` erst DANACH lief, wurde der vom Benutzer gesetzte `is_public=True` Wert durch das Signal wieder ueberschrieben.

2. **Frontend-Payload:** Das Frontend sendete beim PATCH immer das `collections`-Array mit, auch wenn sich nur `is_public` geaendert hatte. Dadurch wurde das `m2m_changed`-Signal bei jedem Speichern ausgeloest.

### Fix 1: Backend - Reihenfolge in serializers.py korrigiert

**Datei:** `backend/server/adventures/serializers.py` - Methode `LocationSerializer.update()`

**Vorher:** `instance.collections.set()` → `instance.save()`
**Nachher:** `instance.save()` → `instance.collections.set()`

Durch das Vertauschen der Reihenfolge wird der vom Benutzer gesetzte `is_public`-Wert zuerst in der Datenbank gespeichert. Das `m2m_changed`-Signal kann ihn danach nicht mehr ueberschreiben, da `instance.save()` bereits abgeschlossen ist.

### Fix 2: Frontend - Unnoetige Collections aus PATCH-Payload entfernt

**Datei:** `frontend/src/lib/components/locations/LocationDetails.svelte` - Funktion `handleSave()`

Beim Erstellen eines PATCH-Payloads wird das `collections`-Feld nur mitgesendet, wenn die Location tatsaechlich zu einer Collection gehoert. Dadurch wird das `m2m_changed`-Signal nicht unnoetig ausgeloest.

### Alle geaenderten Dateien

| Datei | Aenderung |
|-------|-----------|
| `backend/server/adventures/serializers.py` | `save()` vor `collections.set()` in `update()` |
| `frontend/src/lib/components/locations/LocationDetails.svelte` | `collections` nur bei Bedarf im PATCH-Payload |


---

## Bug: "Das Kopieren ist fehlgeschlagen" - Clipboard API in HTTP-Kontexten

**Datum:** 2026-02-10
**Symptom:** Beim Klicken auf "Link kopieren" (Copy Link) auf der Collections- oder Locations-Seite erscheint ein roter Toast "Das Kopieren ist fehlgeschlagen" / "Copy failed". Der Link wird nicht in die Zwischenablage kopiert.
**Ursache:** `navigator.clipboard.writeText()` ist eine Web-API, die einen "Secure Context" erfordert (HTTPS oder localhost). Da die App ueber `http://192.168.178.160:8015` (plain HTTP auf einer LAN-IP) aufgerufen wird, blockiert der Browser den Zugriff auf die Clipboard API.

### Analyse

Alle Clipboard-Aufrufe im Frontend verwendeten direkt `navigator.clipboard.writeText()`:
- `CollectionCard.svelte` - "Link kopieren" bei Collections
- `LocationCard.svelte` - "Link kopieren" bei Locations
- `CollectionModal.svelte` - "Link kopieren" im Collection-Bearbeitungsdialog
- `TOTPModal.svelte` - TOTP-Schluessel kopieren
- `locations/[id]/+page.svelte` - Koordinaten und Google Maps Link kopieren

In einem nicht-sicheren Kontext (HTTP + nicht-localhost) ist `navigator.clipboard` entweder `undefined` oder `writeText()` wirft eine `DOMException`.

### Fix: Globales Clipboard-Polyfill via Server-Side HTML-Injection

**Ansatz:** Statt jeden einzelnen Clipboard-Aufruf zu aendern, wird ein Polyfill-Skript serverseitig in den `<head>` jeder Seite injiziert. Das Polyfill ueberschreibt `navigator.clipboard.writeText` in nicht-sicheren Kontexten mit einem `document.execCommand('copy')` Fallback.

**Vorteile dieses Ansatzes:**
1. Funktioniert mit gecachten JS-Chunks (SvelteKit `immutable` Cache-Headers)
2. Ein einziger Fix fuer ALLE Clipboard-Aufrufe in der gesamten App
3. Kein Patchen einzelner kompilierter JS-Dateien noetig
4. Wird VOR allen SvelteKit-Skripten geladen

#### Das Polyfill-Skript (minifiziert):

```javascript
!function(){
  if(!window.isSecureContext){
    navigator.clipboard||(navigator.clipboard={});
    navigator.clipboard.writeText=function(t){
      return new Promise(function(r){
        var a=document.createElement("textarea");
        a.value=t;
        a.style.position="fixed";
        a.style.left="-9999px";
        a.style.top="-9999px";
        document.body.appendChild(a);
        a.focus();
        a.select();
        try{document.execCommand("copy")}catch(e){}
        document.body.removeChild(a);
        r();
      })
    }
  }
}();
```

**Funktionsweise:**
1. Prueft `!window.isSecureContext` - laeuft nur in nicht-sicheren Kontexten
2. Erstellt `navigator.clipboard` falls nicht vorhanden
3. Ueberschreibt `writeText()` mit einem Fallback:
   - Erstellt ein unsichtbares `<textarea>`-Element
   - Setzt den zu kopierenden Text als Wert
   - Fokussiert und selektiert den Text
   - Fuehrt `document.execCommand('copy')` aus
   - Entfernt das Textarea
   - Resolved die Promise immer (kein Reject, da `execCommand` in manchen Browsern `false` zurueckgibt aber trotzdem funktioniert)

### Geaenderte Dateien

| Datei | Typ | Aenderung |
|-------|-----|-----------|
| `frontend/src/hooks.server.ts` | Quellcode | Clipboard-Polyfill via `transformPageChunk` in `themeHook` injiziert |
| `frontend/src/lib/index.ts` | Quellcode | `copyToClipboard()` Hilfsfunktion hinzugefuegt (fuer lokale Fallback-Logik) |
| `frontend/src/lib/components/cards/CollectionCard.svelte` | Quellcode | Verwendet `copyToClipboard()` statt direktem `navigator.clipboard` |
| `frontend/src/lib/components/cards/LocationCard.svelte` | Quellcode | Verwendet `copyToClipboard()` statt direktem `navigator.clipboard` |
| `frontend/src/lib/components/CollectionModal.svelte` | Quellcode | Verwendet `copyToClipboard()` mit try-catch |
| `frontend/src/lib/components/TOTPModal.svelte` | Quellcode | Verwendet `copyToClipboard()` mit try-catch |
| `frontend/src/routes/locations/[id]/+page.svelte` | Quellcode | Verwendet `copyToClipboard()` fuer Koordinaten/Maps-Link |
| `/app/build/server/chunks/hooks.server-Brt-kPkC.js` | Kompiliert (Container) | Polyfill-Injection in `transformPageChunk` |

### Deployment-Hinweis

- Das Polyfill wird serverseitig in jede HTML-Seite injiziert, daher sofort wirksam nach Container-Neustart
- Browser-Cache spielt keine Rolle, da das Polyfill im HTML-`<head>` steht (nicht in gecachten JS-Chunks)
- Bei Container-Neuerstellung muss die kompilierte `hooks.server-*.js` Datei erneut gepatcht werden, oder ein neuer Build aus dem aktualisierten Quellcode erstellt werden
- Der Quellcode-Fix in `hooks.server.ts` stellt sicher, dass das Polyfill bei jedem kuenftigen Build automatisch enthalten ist


---

## Bug: Ungueltige URLs im Link-Feld verhindern Collection-Speicherung

**Datum:** 2026-02-10
**Symptom:** Wenn im "Link"-Feld einer Collection ein ungueltiger Wert eingegeben wird (z.B. "fff"), kann die Sammlung nicht gespeichert werden. Django gibt `400 Bad Request` mit `{"link": ["Enter a valid URL."]}` zurueck. Der Benutzer bekommt nur eine generische Fehlermeldung.
**Ursache:** Django's `URLField`-Validator (im DRF-Serializer automatisch als `URLField` generiert) lehnt ungueltige URLs ab, bevor der Wert die `validate_link()`-Methode erreicht.

### Analyse

Backend-Log zeigte wiederholte Fehler:
```
Bad Request: /api/collections/92bef4da-2320-4eb3-90de-9a83a94e14ee/
```

Erster Ansatz: Frontend-Validierung (wie bei Locations). Problem: SvelteKit cacht kompilierte JS-Chunks mit `Cache-Control: immutable`. Browser laden die gepatchten Dateien nicht neu, es sei denn der Benutzer macht einen Hard-Reload. Daher ist ein reiner Frontend-Fix unzuverlaessig.

### Fix: Backend-Serializer - link-Feld als CharField mit manueller Validierung

**Datei:** `backend/server/adventures/serializers.py` - `CollectionSerializer`

**Aenderung 1:** Das `link`-Feld wird explizit als `CharField` deklariert (statt des auto-generierten `URLField`):

```python
link = serializers.CharField(required=False, allow_blank=True, allow_null=True)
```

Dadurch passiert der Wert die Feld-Validierung unabhaengig vom Inhalt.

**Aenderung 2:** Eine `validate_link()`-Methode bereinigt den Wert:

```python
def validate_link(self, value):
    """Convert empty or invalid URLs to None so Django doesn't reject them."""
    if not value or not value.strip():
        return None
    from django.core.validators import URLValidator
    from django.core.exceptions import ValidationError as DjangoValidationError
    validator = URLValidator()
    try:
        validator(value)
    except DjangoValidationError:
        return None
    return value
```

**Verhalten:**
- `"fff"` → `None` (ungueltige URL, wird still entfernt)
- `""` → `None` (leerer String, wird zu null)
- `"https://example.com"` → `"https://example.com"` (gueltige URL, wird beibehalten)

### Zusaetzlich: Frontend-Validierung (fuer kuenftige Builds)

**Datei:** `frontend/src/lib/components/CollectionModal.svelte`

Identisch zum Location-Fix - vor dem Senden des Payloads wird das Link-Feld bereinigt:

```javascript
if (!payload.link || !payload.link.trim()) {
    payload.link = null;
} else {
    try { new URL(payload.link); } catch { payload.link = null; }
}
```

Verbesserte Fehlerextraktion fuer Django-Feld-Fehler bei POST und PATCH.

### Alle geaenderten Dateien

| Datei | Typ | Aenderung |
|-------|-----|-----------|
| `backend/server/adventures/serializers.py` | Quellcode + Container | `link` als CharField + `validate_link()` Methode |
| `frontend/src/lib/components/CollectionModal.svelte` | Quellcode | URL-Validierung + Feld-Fehler-Extraktion |

### Deployment-Hinweis

- **Backend-Fix ist sofort wirksam** nach Container-Neustart - kein Browser-Cache-Problem
- Der Frontend-Fix greift erst beim naechsten Build (oder nach Hard-Reload im Browser)
- Die doppelte Validierung (Backend + Frontend) stellt sicher, dass ungueltige URLs in keinem Fall ein Problem verursachen


---

## Feature: Duplicate Location Button

**Datum:** 2026-02-10
**Beschreibung:** Neue Funktion zum schnellen Duplizieren von Locations (Adventures). Ermoeglicht es Benutzern, eine Kopie einer bestehenden Location mit einem Klick zu erstellen.

### Funktionsumfang

- **"Duplicate Location"** Button in der Detail-Ansicht (FAB-Dropdown-Menue mit DotsVertical-Icon)
- **"Duplicate"** Button im Drei-Punkte-Menue der LocationCard (Listenansicht)
- Erstellt eine Kopie mit "Copy of " Praefix im Namen
- Kopiert alle Felder: Beschreibung, Rating, Link, Location, Tags, Kategorie, Preis, Waehrung
- Setzt `is_public` auf `False` (Kopie ist immer privat)
- Kopiert Bild-Referenzen (ContentImage-Zeilen zeigen auf dieselben Dateien - keine Datei-Duplikation)
- Kopiert NICHT: Collections, Visits
- Leitet nach Erstellung zur neuen Location um
- Fehlerbehandlung mit Toast-Nachrichten

### Backend: API-Endpoint

**Datei:** `backend/server/adventures/views/location_view.py`

Neuer `@action(detail=True, methods=['post'])` Endpoint `duplicate` im `LocationViewSet`:

```python
@action(detail=True, methods=['post'])
def duplicate(self, request, pk=None):
    """Create a duplicate of an existing location."""
    original = self.get_object()
    # Permission check
    if not self._has_adventure_access(original, request.user):
        return Response({"error": "..."}, status=403)
    # Atomic transaction
    with transaction.atomic():
        new_location = Location(
            user=request.user,
            name=f"Copy of {original.name}",
            # ... all fields copied ...
            is_public=False,
        )
        # Category: get_or_create for new owner
        # Images: create new ContentImage rows pointing to same files
        new_location.save()
    return Response(serializer.data, status=201)
```

**Route:** `POST /api/locations/{id}/duplicate/`

### Frontend: Detail-Ansicht

**Datei:** `frontend/src/routes/locations/[id]/+page.svelte`

- Ersetzung des einzelnen Edit-FAB-Buttons durch ein Dropdown-Menue (DotsVertical-Icon)
- Menue-Optionen: "Edit Location" und "Duplicate Location"
- `duplicateAdventure()` Funktion mit API-Aufruf und Redirect
- `isFabMenuOpen` State fuer Dropdown-Steuerung

### Frontend: LocationCard (Listenansicht)

**Datei:** `frontend/src/lib/components/cards/LocationCard.svelte`

- "Duplicate" Button im bestehenden Drei-Punkte-Dropdown-Menue
- Erscheint nur fuer den Eigentuemer der Location
- Gleiche `duplicateAdventure()` Logik wie in der Detail-Ansicht

### Frontend: Lokalisierung

**Datei:** `frontend/src/locales/en.json`

Neue Schluessel:
- `adventures.duplicate` - "Duplicate"
- `adventures.duplicate_location` - "Duplicate Location"
- `adventures.location_duplicate_success` - Erfolgsmeldung
- `adventures.location_duplicate_error` - Fehlermeldung

### Alle geaenderten Dateien

| Datei | Aenderung |
|-------|-----------|
| `backend/server/adventures/views/location_view.py` | `duplicate` Action im ViewSet |
| `frontend/src/routes/locations/[id]/+page.svelte` | FAB-Dropdown mit Edit + Duplicate |
| `frontend/src/lib/components/cards/LocationCard.svelte` | Duplicate im Karten-Dropdown |
| `frontend/src/locales/en.json` | Neue Uebersetzungsschluessel |

### Bekanntes Problem: MultipleObjectsReturned bei Bild-Anzeige

**Symptom:** Bilder von duplizierten Locations werden nicht angezeigt (leere Thumbnails/Hero-Section).
**Ursache:** Die Duplicate-Funktion erstellt neue `ContentImage`-Zeilen, die auf dieselben Bilddateien zeigen. In `file_permissions.py` (Zeile 15) wird `ContentImage.objects.get(image=image_path)` aufgerufen, was bei mehreren Eintraegen mit demselben Dateipfad `MultipleObjectsReturned` wirft.

**Empfohlener Fix:** In `adventures/utils/file_permissions.py`:
```python
# Vorher:
content_image = ContentImage.objects.get(image=image_path)
# Nachher:
content_image = ContentImage.objects.filter(image=image_path).first()
```

Alternativ: Bei der Duplikation die Bilddateien physisch kopieren statt auf dieselbe Datei zu verweisen.


---

## Testprotokoll - Browser-Verifizierung (2026-02-10)

Systematische Pruefung aller implementierten Fixes und Features im Browser (http://192.168.178.160:8015):

| # | Test | Status | Details |
|---|------|--------|---------|
| 1 | Login & Dashboard | BESTANDEN | Eingeloggt als admin, Dashboard laedt korrekt |
| 2 | Wikipedia-Bildabruf (Bug #991) | BESTANDEN | Suche "Brandenburger Tor" liefert 8 Ergebnisse, Bild-Upload funktioniert |
| 3 | Duplicate-Button (Feature) | BESTANDEN | FAB-Menue in Detail-Ansicht + Karten-Dropdown funktionieren, "Copy of" Praefix korrekt |
| 4 | Clipboard-Polyfill | TEILWEISE | Polyfill ist im Build, execCommand limitiert in headless Browser |
| 5 | World Map Farben | BESTANDEN | CSS-Injection (oklch) + bg-*-400 im Build, Karte laedt mit sichtbaren Markern |
| 6 | Location erstellen + Save | BESTANDEN | "Koelner Dom" erfolgreich erstellt mit Geocoding |
| 7 | Ungueltige URL abgefangen | BESTANDEN | "ungueltige-url-test" wird zu null konvertiert, Save funktioniert |
| 8 | Public/Private umschalten (Bug #617) | BESTANDEN | Koelner Dom von Private auf Public gewechselt, bleibt nach Speichern erhalten |

### Neuer Bug gefunden waehrend Tests

**ContentImage MultipleObjectsReturned:** Beim Abrufen von Bildern duplizierter Locations wirft `file_permissions.py` einen Fehler, weil mehrere ContentImage-Eintraege auf dieselbe Datei verweisen. Siehe "Bekanntes Problem" im Duplicate-Feature Abschnitt.


---

## Bug: Fehlende i18n-Schluessel fuer Duplicate-Button in allen Nicht-Englischen Sprachen

**Datum:** 2026-02-10
**Symptom:** Der "Duplicate Location" Button im Drei-Punkte-Menue zeigt rohe i18n-Schluessel statt uebersetztem Text an:
- `adventures.duplicate_location` statt "Standort duplizieren" (de) / "Duplicar ubicacion" (es) etc.
- `adventures.location_actions` statt "Standort-Aktionen" (de) / "Location actions" (en) etc.
- "Duplicate" (englischer Fallback) statt der jeweiligen Landessprache

**Ursache:** Bei der Implementierung des Duplicate-Features wurden die neuen i18n-Schluessel nur zur englischen Locale-Datei (`en.json`) hinzugefuegt. Alle 18 weiteren Sprachen hatten die Schluessel nicht. Zusaetzlich fehlte der `location_actions`-Schluessel (aria-label des Drei-Punkte-Buttons) in ALLEN Locales, einschliesslich Englisch.

### Betroffene Schluessel

| Schluessel | Verwendung |
|------------|------------|
| `adventures.duplicate` | Button-Text im Dropdown-Menue |
| `adventures.duplicate_location` | Button-Text im FAB-Menue der Detail-Ansicht |
| `adventures.location_duplicate_success` | Toast-Nachricht bei Erfolg |
| `adventures.location_duplicate_error` | Toast-Nachricht bei Fehler |
| `adventures.location_actions` | aria-label des Drei-Punkte-Menue-Buttons |

### Fix: Uebersetzungen fuer alle 19 Sprachen hinzugefuegt

Alle 19 unterstuetzten Sprachen (en, de, es, fr, it, zh, nl, sv, pl, ko, no, ru, ja, ar, pt-br, sk, tr, uk, hu) erhielten die 5 neuen Schluessel mit korrekten muttersprachlichen Uebersetzungen.

### Geaenderte Dateien

**19 Quell-Locale-Dateien:** `frontend/src/locales/*.json`

Jede Datei erhielt 5 neue Schluessel im `adventures`-Abschnitt (ausser EN das nur `location_actions` brauchte, und DE das bereits alle hatte).

**38 kompilierte Chunks:** Client + Server Chunks fuer alle 19 Sprachen im laufenden Container gepatcht.

### Deployment-Hinweis

- Kompilierte Chunks gepatcht, Container neu gestartet
- Benutzer muessen einmalig Strg+Shift+R (Hard Refresh) ausfuehren
- Bei Container-Neuerstellung: neuer Frontend-Build noetig (`pnpm run build`)


---

## Aktualisiertes Testprotokoll (2026-02-10, Nachtrag)

| # | Test | Status | Details |
|---|------|--------|---------|
| 9 | i18n Duplicate-Button (DE) | BESTANDEN | curl-verifiziert: duplicate:"Duplizieren" |
| 10 | i18n alle 19 Sprachen | BESTANDEN | Stichproben ES, FR, JA, RU, TR bestaetigt |
| 11 | location_actions aria-label | BESTANDEN | EN + DE Chunks enthalten Schluessel |


---

## [FEATURE] Collection (Sammlung/Reise) duplizieren (2026-02-10)

### Beschreibung

Neuer "Duplizieren"-Button fuer Collections (Sammlungen/Reisen) im Dropdown-Menue der CollectionCard, analog zum bestehenden "Duplizieren"-Button fuer Locations (Standorte).

### Backend: `CollectionViewSet.duplicate` Action

**Datei:** `backend/server/adventures/views/collection_view.py`

Neue `@action(detail=True, methods=['post'])` Methode `duplicate()`:
- Erstellt eine Kopie der Collection mit "Copy of" Name-Prefix
- **Kopiert:** Name, Beschreibung, Link
- **Zurueckgesetzt:** is_public=False, is_archived=False, start_date=None, end_date=None, shared_with=leer, locations=leer, itinerary=leer, primary_image=None
- Nur der Eigentuemer kann duplizieren (Permission-Check)
- Verwendet `transaction.atomic()` fuer Datenkonsistenz

### Frontend: CollectionCard.svelte

**Datei:** `frontend/src/lib/components/cards/CollectionCard.svelte`

- ContentCopy-Icon importiert
- `isDuplicating` State-Variable und `duplicateCollection()` Funktion hinzugefuegt
- Neuer "Duplizieren"-Button im Dropdown-Menue (zwischen "ZIP exportieren" und "Loeschen")
- API-Aufruf: `POST /api/collections/{id}/duplicate/`
- Erfolg: Toast-Nachricht + Weiterleitung zur duplizierten Sammlung
- Fehler: Toast-Fehlermeldung

### i18n: 2 neue Schluessel fuer alle 19 Sprachen

| Schluessel | EN | DE |
|---|---|---|
| `collection_duplicate_success` | Collection duplicated successfully! Redirecting... | Sammlung erfolgreich dupliziert! Weiterleitung... |
| `collection_duplicate_error` | Failed to duplicate collection. | Sammlung konnte nicht dupliziert werden. |

Alle 19 Sprachen (en, de, es, fr, it, zh, nl, sv, pl, ko, no, ru, ja, ar, pt-br, sk, tr, uk, hu) aktualisiert.

### Deployment

- Frontend komplett neu gebaut (`npm run build`) im Container
- Backend-Datei per `docker cp` und `docker restart` deployt
- Kein Cache-Busting noetig (komplett neuer Build mit neuen Chunk-Namen)

### Testprotokoll

| # | Test | Status | Details |
|---|------|--------|---------|
| 12 | "Duplizieren" Button sichtbar | BESTANDEN | Im CollectionCard-Dropdown nach "ZIP exportieren" |
| 13 | Button-Text korrekt (DE) | BESTANDEN | Zeigt "Duplizieren" mit ContentCopy-Icon |
| 14 | Kopie erstellen | BESTANDEN | "Copy of Mein Test-Abenteuer" erstellt |
| 15 | Name mit "Copy of" Prefix | BESTANDEN | "Copy of Mein Test-Abenteuer" |
| 16 | Beschreibung kopiert | BESTANDEN | "Eine tolle Testreise nach Berlin" |
| 17 | Datum zurueckgesetzt | BESTANDEN | start_date=null, end_date=null |
| 18 | Locations zurueckgesetzt | BESTANDEN | 0 Standorte in der Kopie |
| 19 | Status zurueckgesetzt | BESTANDEN | is_public=False, is_archived=False |
| 20 | Weiterleitung zur Kopie | BESTANDEN | Automatische Weiterleitung zur duplizierten Sammlung |
| 21 | Original unveraendert | BESTANDEN | "Mein Test-Abenteuer" nach wie vor vorhanden |
| 22 | Standort-Duplicate noch funktional | BESTANDEN | Keine Regression bei bestehender Location-Duplicate-Funktion |
| 23 | Backend API Endpoint | BESTANDEN | POST /api/collections/{id}/duplicate/ gibt 201 mit korrektem JSON |
| 24 | Bilder Standorte | BESTANDEN | Keine Regression - Bilder werden korrekt angezeigt |


---

## Regressions-Fix: Location-Duplizieren-Button fehlte nach Rebuild (2026-02-10)

### Ursache

Beim Frontend-Rebuild fuer das Collection-Duplicate-Feature wurde die Container-interne Version von `LocationCard.svelte` und `locations/[id]/+page.svelte` verwendet. Diese aeltere Version enthielt den zuvor per Chunk-Patch eingefuegten Standort-Duplizieren-Button **nicht** im Quellcode.

### Behebung

Die korrekten Quelldateien aus dem Repository (die den Duplicate-Button enthalten) wurden per `docker cp` in den Container kopiert und das Frontend erneut komplett neu gebaut (`npm run build`).

**Betroffene Dateien:**
- `frontend/src/lib/components/cards/LocationCard.svelte` - enthielt `duplicateAdventure()` Funktion + Button
- `frontend/src/routes/locations/[id]/+page.svelte` - enthielt `duplicateAdventure()` Funktion + FAB-Button

### Verifikation

Nach dem Rebuild enthaelt der kompilierte Build beide Duplicate-Funktionen:
- `locations/.../duplicate/` (Standort duplizieren)
- `collections/.../duplicate/` (Sammlung duplizieren)

### Testprotokoll (Regressions-Fix)

| # | Test | Status | Details |
|---|------|--------|---------|
| 25 | Standort "Duplizieren" Button sichtbar | BESTANDEN | Im LocationCard-Dropdown mit ContentCopy-Icon |
| 26 | Standort-Dropdown vollstaendig | BESTANDEN | Bearbeiten, Duplizieren, Sammlungen, Link kopieren, Loeschen |
| 27 | Sammlung "Duplizieren" Button weiterhin sichtbar | BESTANDEN | Im CollectionCard-Dropdown |
| 28 | Bilder Standorte | BESTANDEN | Keine Regression - Bilder laden korrekt |

### Lessons Learned

Beim Rebuild im Container muessen ALLE geaenderten Quelldateien aus dem Repository kopiert werden, nicht nur die neu hinzugefuegten. Dateien die zuvor nur als kompilierte Chunks gepatcht wurden, muessen ebenfalls im Quellcode vorliegen.
