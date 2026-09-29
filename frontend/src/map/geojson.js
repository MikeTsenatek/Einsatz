import L from 'leaflet'

export const SHOW_TYPES = new Set(['RMHP', 'LZ'])
const icons = {
  RMHP: L.icon({ iconUrl: new URL('../assets/map/tz_halteplatz.svg', import.meta.url).href, iconSize: [50, 50], iconAnchor: [25, 25], popupAnchor: [0, -25] }),
  LZ: L.icon({ iconUrl: new URL('../assets/map/tz_lz.svg', import.meta.url).href, iconSize: [50, 50], iconAnchor: [25, 25], popupAnchor: [0, -25] }),
}
const lineTypes = new Set(['LineString', 'MultiLineString'])
const numeric = (value, fallback, max) => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= max ? value : fallback
export function featureStyle(feature) {
  if (!lineTypes.has(feature?.geometry?.type)) return { color: 'purple', weight: 1 }
  const p = feature.properties || {}
  const color = p.stroke ?? p.color
  return {
    color: typeof color === 'string' && CSS.supports('color', color) ? color : 'blue',
    weight: numeric(p['stroke-width'] ?? p.weight, 4, 100),
    opacity: numeric(p['stroke-opacity'] ?? p.opacity, 0.8, 1),
    dashArray: typeof p.dashArray === 'string' && /^\d+(?:\.\d+)?(?:[ ,]+\d+(?:\.\d+)?)*$/.test(p.dashArray) ? p.dashArray : undefined,
    lineCap: ['butt', 'round', 'square'].includes(p.lineCap) ? p.lineCap : 'round',
    lineJoin: ['miter', 'round', 'bevel'].includes(p.lineJoin) ? p.lineJoin : 'round',
  }
}

// Rebuild a small formatting subset as DOM nodes; never bind imported HTML directly.
export function popupContent(content) {
  const template = document.createElement('template')
  template.innerHTML = content
  const result = document.createElement('div')
  const allowed = new Set(['B', 'STRONG', 'I', 'EM', 'U', 'P', 'BR', 'DIV', 'SPAN', 'UL', 'OL', 'LI', 'TABLE', 'THEAD', 'TBODY', 'TR', 'TH', 'TD', 'H3', 'H4', 'A'])
  const blocked = new Set(['SCRIPT', 'STYLE', 'IFRAME', 'OBJECT', 'EMBED', 'SVG', 'MATH', 'TEMPLATE', 'IMG', 'LINK', 'META'])
  function copy(source, target) {
    for (const node of source.childNodes) {
      if (node.nodeType === Node.TEXT_NODE) { target.append(document.createTextNode(node.textContent)); continue }
      if (node.nodeType !== Node.ELEMENT_NODE || blocked.has(node.tagName)) continue
      if (!allowed.has(node.tagName)) { copy(node, target); continue }
      const element = document.createElement(node.tagName.toLowerCase())
      if (node.tagName === 'A') {
        try {
          const url = new URL(node.getAttribute('href'), document.baseURI)
          if (node.hasAttribute('href') && ['https:', 'http:'].includes(url.protocol)) {
            element.href = url.href; element.target = '_blank'; element.rel = 'noopener noreferrer'
          }
        } catch { /* Keep the link's text when its URL is invalid. */ }
      }
      copy(node, element); target.append(element)
    }
  }
  copy(template.content, result)
  return result
}
const hasPopup = f => typeof f?.properties?.popupContent === 'string' && Boolean(f.properties.popupContent.trim())
function bindPopup(feature, layer) {
  if (hasPopup(feature)) layer.bindPopup(() => popupContent(feature.properties.popupContent))
}

export function createGeoJSONLayers(data, searchRenderer) {
  const featureLayers = new Map()
  const registerFeatureLayer = (feature, layer) => {
    featureLayers.set(feature, layer)
    bindPopup(feature, layer)
  }
  const visibleLayer = L.geoJSON(data, {
    pane: 'geojsonPane',
    filter: f => lineTypes.has(f.geometry?.type) || SHOW_TYPES.has(f.properties?.type),
    interactive: false,
    bubblingMouseEvents: false,
    pointToLayer: (feature, latlng) => {
      const type = feature.properties?.type
      return icons[type]
        ? L.marker(latlng, { icon: icons[type], alt: type, title: type, bubblingMouseEvents: false })
        : L.circleMarker(latlng, { radius: 6, color: 'purple', bubblingMouseEvents: false })
    },
    style: featureStyle,
    onEachFeature: registerFeatureLayer,
  })
  const searchLayer = L.geoJSON(data, {
    pane: 'searchPane', renderer: searchRenderer,
    bubblingMouseEvents: false,
    pointToLayer: (feature, latlng) => L.circleMarker(latlng, {
      pane: 'searchPane', renderer: searchRenderer, radius: 10, weight: 10,
      opacity: 0.001, fillOpacity: 0.001, interactive: hasPopup(feature), bubblingMouseEvents: false,
    }),
    style: feature => ({ color: '#000', weight: 12, opacity: 0, fillOpacity: 0, interactive: hasPopup(feature), bubblingMouseEvents: false }),
    onEachFeature: registerFeatureLayer,
  })
  const layers = L.featureGroup([visibleLayer, searchLayer])
  layers.featureLayers = featureLayers
  return layers
}
