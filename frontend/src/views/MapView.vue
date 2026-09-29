<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { api } from '../api'
import { createGeoJSONLayers } from '../map/geojson'
import { calibrate, cornerKeys, legacyPoints, validLocation, project, unproject } from '../map/calibration'

const props = defineProps({ mission: Object, user: Object })
const canvas = ref(null)
const editing = ref(false)
const editorOpen = ref(false)
const imageInput = ref(null)
const pointsInput = ref(null)
const geojsonInput = ref(null)
const geojsonCount = ref(0)
const geojsonImports = ref([])
const geojsonSearchField = ref('StandnummerohneGruppe')
const geojsonSearch = ref('')
const geojsonSearchConfigOpen = ref(false)
const selectedSearchFields = ref([])
const selectedResultFields = ref([])
const searchConfigReady = ref(false)
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const selectedPoint = ref(0)
const imageAspect = ref(1)
const empty = () => ({ name: '', image: '', opacity: 0.85, control_points: [], corners: null, geojson_search_fields: [], geojson_result_fields: [] })
function restore(data) {
  const result = structuredClone(data || empty())
  if (result.control_points == null) result.control_points = result.corners ? legacyPoints(result.corners) : []
  if (!Array.isArray(result.geojson_search_fields)) result.geojson_search_fields = []
  if (!Array.isArray(result.geojson_result_fields)) result.geojson_result_fields = []
  return result
}
const draft = ref(empty())
let saved = null
let map, overlay, markers, observer, geojsonLayers, searchRenderer
let disposed = false
const controller = new AbortController()
const calibration = computed(() => {
  try { return calibrate(draft.value.control_points, draft.value.corners) }
  catch (e) { return { error: e.message } }
})
const validPoints = computed(() => !calibration.value.error)
const normalizeFieldKey = key => key.replace(/[^a-z0-9]/gi, '').toLowerCase()
const displayFieldLabel = key => {
  const normalized = normalizeFieldKey(key)
  if (normalized === 'standnummerohnegruppe') return 'Standnummer ohne Gruppe'
  if (normalized === 'standnummer') return 'Standnummer'
  if (normalized === 'name') return 'Name'
  return key
}
const geojsonSearchFields = computed(() => {
  const fields = new Map()
  for (const imported of geojsonImports.value) {
    const features = imported.data?.type === 'FeatureCollection'
      ? imported.data.features
      : imported.data?.type === 'Feature' ? [imported.data] : [{ geometry: imported.data, properties: {} }]
    for (const feature of features) {
      for (const [key, value] of Object.entries(feature.properties || {})) {
        if (key !== 'popupContent' && value != null && ['string', 'number', 'boolean'].includes(typeof value) && !fields.has(normalizeFieldKey(key))) fields.set(normalizeFieldKey(key), key)
      }
    }
  }
  return [...fields.values()].sort((a, b) => {
    const rank = key => ['standnummerohnegruppe', 'standnummer', 'name'].indexOf(normalizeFieldKey(key))
    return (rank(a) < 0 ? 3 : rank(a)) - (rank(b) < 0 ? 3 : rank(b)) || a.localeCompare(b, 'de')
  }).map(value => ({ value, label: displayFieldLabel(value) }))
})
const fieldLabel = key => displayFieldLabel(key)
function initializeSearchConfig() {
  const fields = geojsonSearchFields.value
  if (!fields.length) return
  const available = fields.map(field => field.value)
  const defaults = available.filter(key => ['standnummerohnegruppe', 'name'].includes(key.toLowerCase()))
  const defaultFields = defaults.length ? defaults : available
  const savedSearchFields = draft.value.geojson_search_fields.length ? draft.value.geojson_search_fields : defaultFields
  const savedResultFields = draft.value.geojson_result_fields.length ? draft.value.geojson_result_fields : defaults.length ? defaults : available.slice(0, 2)
  selectedSearchFields.value = savedSearchFields.filter(key => available.includes(key))
  selectedResultFields.value = savedResultFields.filter(key => available.includes(key))
  if (!selectedSearchFields.value.length) selectedSearchFields.value = available.slice(0, 1)
  if (!selectedResultFields.value.length) selectedResultFields.value = available.slice(0, 1)
  geojsonSearchField.value = selectedSearchFields.value.includes(geojsonSearchField.value) ? geojsonSearchField.value : selectedSearchFields.value[0]
  searchConfigReady.value = true
}
watch([selectedSearchFields, selectedResultFields, geojsonSearchField], () => {
  if (!searchConfigReady.value) return
  draft.value.geojson_search_fields = [...selectedSearchFields.value]
  draft.value.geojson_result_fields = [...selectedResultFields.value]
}, { deep: true })
function toggleSearchField(field) {
  if (selectedSearchFields.value.includes(field)) {
    if (selectedSearchFields.value.length === 1) return
    selectedSearchFields.value = selectedSearchFields.value.filter(value => value !== field)
    if (geojsonSearchField.value === field) geojsonSearchField.value = selectedSearchFields.value[0]
  } else selectedSearchFields.value = [...selectedSearchFields.value, field]
}
function toggleResultField(field) {
  if (selectedResultFields.value.includes(field)) {
    if (selectedResultFields.value.length === 1) return
    selectedResultFields.value = selectedResultFields.value.filter(value => value !== field)
  } else selectedResultFields.value = [...selectedResultFields.value, field]
}
async function saveSearchConfig() {
  busy.value = true; error.value = ''; notice.value = ''
  try {
    saved = await api(`/missions/${props.mission.id}/map/`, {
      method: 'PATCH',
      body: JSON.stringify({ geojson_search_fields: selectedSearchFields.value, geojson_result_fields: selectedResultFields.value }),
      signal: controller.signal,
    })
    draft.value = restore({ ...draft.value, ...saved })
    notice.value = 'Suchkonfiguration gespeichert.'
  } catch (e) { if (!disposed) error.value = e.message }
  finally { busy.value = false }
}
watch(selectedSearchFields, fields => {
  if (!fields.includes(geojsonSearchField.value)) geojsonSearchField.value = fields[0] || ''
})
const searchResults = computed(() => {
  const query = geojsonSearch.value.trim().toLowerCase()
  if (!query) return []
  const property = geojsonSearchField.value
  const results = []
  const propertyValue = (properties, wanted) => properties[wanted] ?? Object.entries(properties).find(([key]) => normalizeFieldKey(key) === normalizeFieldKey(wanted))?.[1]
  for (const imported of geojsonImports.value) {
    const features = imported.data?.type === 'FeatureCollection'
      ? imported.data.features
      : imported.data?.type === 'Feature' ? [imported.data] : [{ type: 'Feature', geometry: imported.data, properties: {} }]
    features.forEach((feature, index) => {
      const properties = feature.properties || {}
      const value = propertyValue(properties, property)
      if (value != null && String(value).toLowerCase().includes(query)) {
        const resultFields = selectedResultFields.value.map(field => `${fieldLabel(field)}: ${propertyValue(properties, field) ?? '—'}`)
        results.push({ imported, feature, index, label: String(value), resultFields })
      }
    })
  }
  return results.slice(0, 8)
})
function placeInView() {
  if (!map) return
  const bounds = map.getBounds(), a = project({ lat: Math.min(84, bounds.getNorth()), lng: Math.max(-179, bounds.getWest()) })
  const b = project({ lat: Math.max(-84, bounds.getSouth()), lng: Math.min(179, bounds.getEast()) })
  const width = Math.min(Math.abs(b.x-a.x)*0.6, Math.abs(a.y-b.y)*0.6*imageAspect.value)
  const height = width / imageAspect.value, x = (a.x+b.x)/2, y = (a.y+b.y)/2
  draft.value.corners = { topLeft: unproject({x:x-width/2,y:y+height/2}), topRight: unproject({x:x+width/2,y:y+height/2}), bottomLeft: unproject({x:x-width/2,y:y-height/2}) }
}
function addPoint() {
  editorOpen.value = true
  if (validPoints.value) draft.value.corners = calibration.value.corners
  draft.value.control_points.push({ x: null, y: null, lat: null, lng: null })
  selectedPoint.value = draft.value.control_points.length - 1
}
function removePoint(index) {
  if (validPoints.value) draft.value.corners = calibration.value.corners
  draft.value.control_points.splice(index, 1)
  selectedPoint.value = Math.max(0, Math.min(selectedPoint.value, draft.value.control_points.length - 1))
}
function selectImagePosition(event) {
  if (busy.value) return
  if (!draft.value.control_points.length) addPoint()
  const rect = event.currentTarget.getBoundingClientRect()
  const p = draft.value.control_points[selectedPoint.value]
  p.x = Math.max(0, Math.min(1, (event.clientX-rect.left)/rect.width))
  p.y = Math.max(0, Math.min(1, (event.clientY-rect.top)/rect.height))
}
function render() {
  if (!map) return
  markers.clearLayers()
  if (editing.value) draft.value.control_points.forEach((p, index) => {
    if (!validLocation(p)) return
    L.marker([p.lat, p.lng], { draggable: !busy.value,
      icon: L.divIcon({ className: 'map-control-point', html: String(index + 1), iconSize: [26, 26], iconAnchor: [13, 13] }),
    }).bindTooltip(`Stützpunkt ${index + 1}`).on('click', () => { selectedPoint.value = index }).on('dragend', e => {
      const location = e.target.getLatLng().wrap()
      p.lat = Number(location.lat.toFixed(7)); p.lng = Number(location.lng.toFixed(7))
    }).addTo(markers)
  })
  // Incomplete new pairs keep the last valid overlay visible while placing them.
  if (!draft.value.image) { overlay?.remove(); overlay = null; return }
  const corners = validPoints.value ? calibration.value.corners : draft.value.corners
  if (!corners) return
  const coords = cornerKeys.map(key => L.latLng(corners[key]))
  if (overlay) {
    if (overlay._url !== draft.value.image) overlay.setUrl(draft.value.image)
    overlay.reposition(...coords)
    overlay.setOpacity(draft.value.opacity)
  } else {
    overlay = L.imageOverlay.rotated(draft.value.image, ...coords, {
      opacity: draft.value.opacity, pane: 'svgPane', interactive: false,
    }).addTo(map)
  }
}
function fit() {
  const bounds = L.latLngBounds([])
  if (overlay) bounds.extend(overlay.getBounds())
  if (geojsonLayers?.getBounds().isValid()) bounds.extend(geojsonLayers.getBounds())
  if (bounds.isValid()) map.fitBounds(bounds, { padding: [20, 20], maxZoom: 20, animate: false })
}
function focusSearchResult(result) {
  const layer = result.imported.geojsonLayer?.featureLayers.get(result.feature)
  if (!layer) return
  const bounds = layer.getBounds()
  if (bounds.isValid()) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 18, animate: true })
  if (typeof layer.openPopup === 'function' && result.feature.properties?.popupContent?.trim()) {
    layer.openPopup()
  }
  geojsonSearch.value = ''
}
async function importGeoJSON(event) {
  const file = event.target.files[0]
  if (!file) return
  busy.value = true; error.value = ''; notice.value = ''
  try {
    if (file.size > 1024 * 1024) throw new Error('GeoJSON darf maximal 1 MB groß sein.')
    const data = JSON.parse(await file.text())
    if (disposed) return
    const imported = await api(`/missions/${props.mission.id}/map/geojson/`, {
      method: 'POST', body: JSON.stringify({ name: file.name, data }), signal: controller.signal,
    })
    if (disposed) return
    const layer = createGeoJSONLayers(imported.data, searchRenderer).addTo(geojsonLayers)
    imported.geojsonLayer = layer
    geojsonImports.value.push(imported)
    if (!searchConfigReady.value) initializeSearchConfig()
    geojsonCount.value += 1
    if (layer.getBounds().isValid()) map.fitBounds(layer.getBounds(), { padding: [30, 30], maxZoom: 18, animate: false })
    notice.value = `${imported.name} importiert.`
  } catch (e) { if (!disposed) error.value = `GeoJSON-Import fehlgeschlagen: ${e.message}` }
  finally { busy.value = false; event.target.value = '' }
}
function begin() { selectedPoint.value = 0; editorOpen.value = true; editing.value = true; notice.value = ''; error.value = '' }
function cancel() { draft.value = restore(saved); editing.value = false; error.value = ''; notice.value = '' }
async function imageFile(event) {
  const file = event.target.files[0]
  if (!file) return
  error.value = ''; notice.value = ''
  if (file.size > 1024 * 1024 || !['image/svg+xml', 'image/png', 'image/jpeg', 'image/gif', 'image/webp'].includes(file.type)) {
    error.value = 'Bitte SVG, PNG, JPEG, GIF oder WebP bis 1 MB auswählen.'; event.target.value = ''; return
  }
  busy.value = true
  try {
    const url = await new Promise((resolve, reject) => {
      const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(file)
    })
    const aspect = await new Promise((resolve, reject) => { const img = new Image(); img.onload = () => resolve(img.naturalWidth / img.naturalHeight); img.onerror = reject; img.src = url })
    if (disposed) return
    imageAspect.value = aspect || 1
    draft.value.image = url; draft.value.name = file.name
    draft.value.control_points = []; selectedPoint.value = 0
    placeInView()
  } catch { error.value = 'Die Bilddatei konnte nicht geladen werden.' }
  finally { busy.value = false; event.target.value = '' }
}
async function importCorners(event) {
  const file = event.target.files[0]
  if (!file) return
  busy.value = true; error.value = ''
  try {
    if (file.size > 1024 * 1024) throw new Error('JSON-Datei ist zu groß.')
    const data = JSON.parse(await file.text())
    if (disposed) return
    const legacy = cornerKeys.every(key => validLocation(data[key]))
    const corners = legacy ? data : (data.corners || draft.value.corners)
    const points = legacy ? legacyPoints(data) : data.control_points
    const result = calibrate(points, corners)
    draft.value.corners = result.corners
    draft.value.control_points = points
    selectedPoint.value = 0
    render(); fit()
  } catch (e) { error.value = `Stützpunkte konnten nicht importiert werden: ${e.message}` }
  finally { busy.value = false; event.target.value = '' }
}
function downloadJson(data, filename) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url)
}
function exportPoints() {
  downloadJson({ corners: calibration.value.corners, control_points: draft.value.control_points }, 'overlay_points.json')
}
function exportCorners() { downloadJson(calibration.value.corners, 'overlay_corners.json') }
async function save() {
  busy.value = true; error.value = ''; notice.value = ''
  try {
    saved = await api(`/missions/${props.mission.id}/map/`, { method: 'PUT', body: JSON.stringify({ ...draft.value, corners: calibration.value.corners }), signal: controller.signal })
    draft.value = restore(saved); editing.value = false; notice.value = 'Kartenoverlay gespeichert.'
  } catch (e) { if (!disposed) error.value = e.message }
  finally { busy.value = false }
}
watch([draft, editing, busy], render, { deep: true })
onMounted(async () => {
  try {
    // The plugin extends the global Leaflet object.
    window.L = L
    await import('leaflet-imageoverlay-rotated')
    if (disposed) return
    map = L.map(canvas.value, { zoomControl: false }).setView([51.16, 10.45], 6)
    L.control.zoom({ position: 'bottomright' }).addTo(map)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', maxZoom: 19,
    }).addTo(map)
    map.createPane('svgPane').style.zIndex = 450
    map.getPane('svgPane').style.pointerEvents = 'none'
    map.createPane('searchPane').style.zIndex = 460
    map.createPane('geojsonPane').style.zIndex = 470
    searchRenderer = L.canvas({ pane: 'searchPane' })
    geojsonLayers = L.featureGroup().addTo(map)
    markers = L.layerGroup().addTo(map)
    map.on('click', e => {
      if (!editing.value || busy.value || !draft.value.control_points.length) return
      const location = e.latlng.wrap()
      const p = draft.value.control_points[selectedPoint.value]
      p.lat = Number(location.lat.toFixed(7)); p.lng = Number(location.lng.toFixed(7))
    })
    observer = new ResizeObserver(() => map?.invalidateSize()); observer.observe(canvas.value)
    const [overlayResult, geojsonResult] = await Promise.allSettled([
      api(`/missions/${props.mission.id}/map/`, { signal: controller.signal }),
      api(`/missions/${props.mission.id}/map/geojson/`, { signal: controller.signal }),
    ])
    if (disposed) return
    const failures = []
    if (overlayResult.status === 'fulfilled') {
      saved = overlayResult.value; draft.value = restore(saved); render()
    } else failures.push(overlayResult.reason.message)
    if (geojsonResult.status === 'fulfilled') {
      geojsonImports.value = geojsonResult.value
      for (const imported of geojsonResult.value) {
        imported.geojsonLayer = createGeoJSONLayers(imported.data, searchRenderer).addTo(geojsonLayers)
      }
      geojsonCount.value = geojsonResult.value.length
      initializeSearchConfig()
    } else failures.push(geojsonResult.reason.message)
    error.value = failures.join(' · ')
    fit()
  } catch (e) { if (!disposed) error.value = e.message || 'Karte konnte nicht geladen werden.' }
  finally { loading.value = false }
})
onBeforeUnmount(() => { disposed = true; controller.abort(); observer?.disconnect(); map?.remove(); map = null })
</script>

<template>
  <section class="map-view" aria-label="Karte">
    <div ref="canvas" class="map-canvas" aria-label="Einsatzkarte" />
    <div class="map-controls">
      <div class="map-toolbar" role="group" aria-label="Kartenaktionen">
        <button :disabled="(!validPoints || !draft.image) && !geojsonCount" title="Karteninhalte anzeigen" @click="fit">⌖ Ausschnitt</button>
        <button v-if="user?.is_staff && !editing" :disabled="loading || !map" @click="begin">Adminmodus</button>
        <template v-if="editing">
          <button :disabled="busy" @click="imageInput.click()">Grafik laden</button>
          <button :disabled="busy" @click="geojsonInput.click()">GeoJSON importieren</button>
          <button :disabled="busy || !draft.image" @click="addPoint">＋ Stützpunkt</button>
          <button :aria-expanded="editorOpen" aria-controls="map-editor" @click="editorOpen = !editorOpen">Stützpunkte {{ draft.control_points.length }} <span aria-hidden="true">{{ editorOpen ? '▴' : '▾' }}</span></button>
          <button class="save-button" :disabled="busy || !draft.image || !validPoints" @click="save">{{ busy ? 'Speichert …' : 'Speichern' }}</button>
          <button :disabled="busy" @click="cancel">Abbrechen</button>
        </template>
      </div>
      <div class="map-search" role="search">
        <label for="geojson-search-field">GeoJSON suchen</label>
        <div class="map-search-fields">
          <select id="geojson-search-field" v-model="geojsonSearchField" aria-label="Suchfeld">
            <option v-for="field in geojsonSearchFields.filter(field => selectedSearchFields.includes(field.value))" :key="field.value" :value="field.value">{{ field.label }}</option>
          </select>
          <input id="geojson-search" v-model="geojsonSearch" type="search" :placeholder="geojsonSearchField ? `${geojsonSearchField} suchen` : 'Suchfeld auswählen'" :disabled="!geojsonSearchFields.length" autocomplete="off" />
        </div>
        <details class="search-settings" :open="geojsonSearchConfigOpen" @toggle="geojsonSearchConfigOpen = $event.target.open">
          <summary>Suchfelder einstellen</summary>
          <fieldset>
            <legend>Durchsuchen</legend>
            <label v-for="field in geojsonSearchFields" :key="`search-${field.value}`"><input type="checkbox" :checked="selectedSearchFields.includes(field.value)" @change="toggleSearchField(field.value)" /> {{ field.label }}</label>
          </fieldset>
          <fieldset>
            <legend>Im Treffer anzeigen</legend>
            <label v-for="field in geojsonSearchFields" :key="`result-${field.value}`"><input type="checkbox" :checked="selectedResultFields.includes(field.value)" @change="toggleResultField(field.value)" /> {{ field.label }}</label>
          </fieldset>
          <button v-if="user?.is_staff" type="button" :disabled="busy" @click="saveSearchConfig">Suchkonfiguration speichern</button>
        </details>
        <div v-if="searchResults.length" class="search-results" role="listbox" aria-label="Suchergebnisse">
          <button v-for="result in searchResults" :key="`${result.imported.id}-${result.index}`" type="button" role="option" @click="focusSearchResult(result)">
            <strong v-for="field in result.resultFields" :key="field">{{ field }}</strong><small>{{ result.imported.name }} · {{ result.feature.geometry?.type }}</small>
          </button>
        </div>
        <p v-else-if="geojsonSearch.trim() && geojsonImports.length" class="search-empty">Keine Treffer</p>
      </div>
      <input ref="imageInput" class="file-input" type="file" aria-label="Grafik (max. 1 MB)" accept=".svg,.png,.jpg,.jpeg,.gif,.webp" :disabled="busy" @change="imageFile" />
      <input ref="geojsonInput" class="file-input" type="file" aria-label="GeoJSON-Datei" accept=".geojson,.json,application/geo+json,application/json" :disabled="busy" @change="importGeoJSON" />
      <input ref="pointsInput" class="file-input" type="file" aria-label="Stützpunkte importieren" accept=".json,application/json" :disabled="busy" @change="importCorners" />
      <p v-if="loading" class="map-message" role="status">Karte wird geladen …</p>
      <p v-if="error" class="map-message map-error" role="alert">{{ error }} <button aria-label="Fehlermeldung schließen" @click="error = ''">×</button></p>
      <p v-if="notice" class="map-message" role="status">{{ notice }} <button aria-label="Meldung schließen" @click="notice = ''">×</button></p>
      <form v-if="editing && editorOpen" id="map-editor" class="map-editor" @submit.prevent="save">
        <fieldset :disabled="busy">
          <div class="editor-heading"><strong :title="draft.name">{{ draft.name || 'Grafik laden' }}</strong><button type="button" aria-label="Stützpunkte einklappen" @click="editorOpen = false">×</button></div>
          <div v-if="draft.image" class="image-picker" @click="selectImagePosition">
            <img class="map-preview" :src="draft.image" alt="Bildpunkt auswählen" @load="imageAspect = $event.target.naturalWidth / $event.target.naturalHeight || 1" />
            <template v-for="(point, index) in draft.control_points" :key="index">
              <button v-if="Number.isFinite(point.x) && Number.isFinite(point.y)" type="button" class="image-point" :class="{ selected: selectedPoint === index }" :style="{ left: `${point.x*100}%`, top: `${point.y*100}%` }" :aria-label="`Bildpunkt ${index + 1} auswählen`" @click.stop="selectedPoint = index">{{ index + 1 }}</button>
            </template>
          </div>
          <p v-if="draft.image" class="point-hint">Bildpunkt wählen → Kartenpunkt setzen</p>
          <div v-if="draft.control_points.length" class="point-tabs" role="group" aria-label="Stützpunkt auswählen">
            <button v-for="(_, index) in draft.control_points" :key="index" type="button" :aria-label="`Stützpunkt ${index + 1}`" :aria-pressed="selectedPoint === index" @click="selectedPoint = index">{{ index + 1 }}</button>
            <button type="button" class="remove-point" :aria-label="`Stützpunkt ${selectedPoint + 1} entfernen`" @click="removePoint(selectedPoint)">Entfernen</button>
          </div>
          <template v-for="(point, index) in draft.control_points" :key="index">
            <details v-if="selectedPoint === index" class="point-row">
              <summary>Koordinaten · Punkt {{ index + 1 }}</summary>
              <div class="coordinates">
                <label>Bild X (0–1)<input v-model.number="point.x" type="number" min="0" max="1" step="any" required /></label>
                <label>Bild Y (0–1)<input v-model.number="point.y" type="number" min="0" max="1" step="any" required /></label>
                <label>Breitengrad<input v-model.number="point.lat" type="number" min="-85" max="85" step="any" required /></label>
                <label>Längengrad<input v-model.number="point.lng" type="number" min="-180" max="180" step="any" required /></label>
              </div>
              <small v-if="validPoints && draft.control_points.length > 3">Abweichung: {{ calibration.residuals[index].toFixed(1) }} m</small>
            </details>
          </template>
          <p v-if="draft.image && !validPoints" class="map-error" role="status">{{ calibration.error }}</p>
          <label v-if="draft.image" class="opacity-control">Deckkraft <input v-model.number="draft.opacity" type="range" min="0" max="1" step="0.01" /> <span>{{ Math.round(draft.opacity * 100) }} %</span></label>
          <details class="file-actions">
            <summary>Import / Export</summary>
            <div class="map-actions">
              <button type="button" @click="pointsInput.click()">JSON importieren</button>
              <button type="button" :disabled="!validPoints" @click="exportPoints">Stützpunkte exportieren</button>
              <button type="button" :disabled="!validPoints" @click="exportCorners">Ecken exportieren</button>
            </div>
          </details>
          <button v-if="draft.image && !draft.control_points.length" type="button" class="place-button" @click="placeInView">Hier platzieren</button>
        </fieldset>
      </form>
    </div>
  </section>
</template>

<style scoped>
.map-view{position:relative;height:calc(100vh - 90px);height:calc(100dvh - 90px);min-height:360px;isolation:isolate}
.map-canvas{position:absolute;inset:0;z-index:0}
.map-controls{position:absolute;inset:12px 12px 48px;z-index:1;display:flex;flex-direction:column;align-items:flex-start;gap:8px;pointer-events:none}
.map-toolbar{display:flex;flex-wrap:wrap;gap:6px;flex-shrink:0}
.map-toolbar button,.map-editor,.map-message{pointer-events:auto;box-shadow:0 2px 10px #102a3d25}
.map-search{position:relative;pointer-events:auto;width:min(340px,100%);background:#fff;padding:8px;border-radius:6px;box-shadow:0 2px 10px #102a3d25}
.map-search label{display:block;font-size:11px;color:#60717b;margin-bottom:4px}
.map-search-fields{display:grid;grid-template-columns:125px minmax(0,1fr);gap:5px}
.map-search select,.map-search input{width:100%;box-sizing:border-box;border:1px solid #c7d2d8;border-radius:4px;padding:8px;color:#263d4c;background:#fff}
.search-settings{margin-top:8px;border-top:1px solid #e5ecef;padding-top:6px}
.search-settings summary{cursor:pointer;color:#48616f;font-size:12px}
.search-settings fieldset{border:0;margin:8px 0 0;padding:0;display:flex;flex-wrap:wrap;gap:4px 10px}
.search-settings legend{width:100%;font-size:11px;color:#60717b;margin-bottom:3px}
.search-settings label{display:flex;align-items:center;gap:3px;font-size:12px;color:#263d4c;margin:0}
.search-settings input{width:auto;padding:0}
.search-results{margin-top:6px;background:#fff;border:1px solid #d7e0e4;border-radius:4px;overflow:hidden;z-index:3}
.search-results button{display:block;width:100%;text-align:left;border-radius:0;border-bottom:1px solid #edf1f2;padding:8px 10px}
.search-results button:last-child{border-bottom:0}
.search-results strong,.search-results small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.search-results small{color:#60717b;font-size:11px;margin-top:2px}
.search-empty{font-size:12px;margin:6px 0 0;color:#60717b}
.map-view button{border:0;border-radius:5px;background:#fff;color:#263d4c;padding:9px 12px;font-size:13px;line-height:1.2}
.map-view button:hover:not(:disabled){background:#edf3f6}
.map-toolbar .save-button{background:#214f67;color:#fff}
.map-toolbar .save-button:hover:not(:disabled){background:#163c50}
.map-editor{width:300px;max-width:100%;min-height:0;overflow-y:auto;padding:12px;background:#fff;border-radius:6px}
.map-editor fieldset{border:0;padding:0;margin:0;min-width:0}
.editor-heading{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:13px}
.editor-heading strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.editor-heading button{padding:3px 7px;font-size:20px}
.map-editor p{font-size:12px;line-height:1.4;margin:10px 0}
.map-editor .point-hint{color:#60717b}
.map-editor label{display:block;margin:8px 0;font-size:11px}
.map-editor input{width:100%;margin-top:4px;padding:7px;border-radius:4px}
.coordinates{display:grid;grid-template-columns:1fr 1fr;gap:0 8px}
.point-tabs,.map-actions{display:flex;flex-wrap:wrap;gap:4px}
.point-tabs button{background:#eef2f4;min-width:30px;padding:7px}
.point-tabs button[aria-pressed=true]{background:#214f67;color:white}
.point-tabs .remove-point{margin-left:auto;background:transparent;color:#9b3d38;font-size:12px}
.map-editor details{margin-top:12px;font-size:12px}
.map-editor summary{cursor:pointer;padding:3px 0;color:#4a626f}
.map-editor small{display:block;margin-top:6px;color:#60717b}
.map-actions{margin-top:6px}.map-actions button{background:#eef2f4;font-size:11px;padding:7px}
.map-editor .opacity-control{display:flex;align-items:center;gap:8px;margin:12px 0 0;font-weight:400;white-space:nowrap}
.opacity-control input{min-width:0;flex:1;margin:0;padding:0;box-shadow:none}
.map-editor .place-button{margin-top:10px;background:#eef2f4;font-size:12px}
.image-picker{position:relative;margin:12px 0;cursor:crosshair}
.map-preview{width:100%;height:auto;display:block}
.map-view .image-point{position:absolute;transform:translate(-50%,-50%);width:24px;height:24px;border:2px solid white;border-radius:50%;padding:0;background:#a52d2d;color:white;line-height:20px;font-weight:bold}
.map-view .image-point.selected{background:#145ca1;outline:2px solid #145ca1}
.map-message{display:flex;align-items:center;gap:10px;max-width:min(480px,100%);padding:8px 12px;margin:0;background:white;border-radius:5px;font-size:12px;flex-shrink:0}
.map-message button{margin-left:auto;padding:0 4px;font-size:18px;background:transparent}
.map-error{color:#a1443e}.file-input{display:none}
.map-view :deep(.map-control-point){background:#a52d2d;border:2px solid white;border-radius:50%;color:white;font-weight:bold;text-align:center;line-height:22px;box-shadow:0 1px 5px #555}
.map-canvas :deep(img){max-width:none}
@media(max-width:760px){.map-controls{inset:8px 8px 48px}.map-toolbar{gap:4px}.map-toolbar button{padding:8px;font-size:12px}.map-editor{width:260px;max-height:50%;padding:10px}}
</style>
