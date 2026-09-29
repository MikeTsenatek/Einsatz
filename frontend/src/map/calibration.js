// All fitting happens in Leaflet's Web Mercator plane, in metres.
const R = 6378137
export const cornerKeys = ['topLeft', 'topRight', 'bottomLeft']
const imageCorners = [[0, 0], [1, 0], [0, 1]]
export function validLocation(p) {
  return p && Number.isFinite(p.lat) && Number.isFinite(p.lng) && Math.abs(p.lat) <= 85 && Math.abs(p.lng) <= 180
}
export function project(p) {
  return { x: R * p.lng * Math.PI / 180, y: R * Math.log(Math.tan(Math.PI / 4 + p.lat * Math.PI / 360)) }
}
export function unproject(p) {
  return { lat: (2 * Math.atan(Math.exp(p.y / R)) - Math.PI / 2) * 180 / Math.PI, lng: p.x / R * 180 / Math.PI }
}
export function legacyPoints(corners) {
  return cornerKeys.map((key, i) => ({ x: imageCorners[i][0], y: imageCorners[i][1], ...corners[key] }))
}
export function validPoint(p) {
  return validLocation(p) && Number.isFinite(p.x) && Number.isFinite(p.y) && p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1
}
function baseTransform(corners) {
  if (!cornerKeys.every(key => validLocation(corners?.[key]))) throw Error('Bitte die Grafik zuerst im Kartenausschnitt platzieren.')
  const [a, b, c] = cornerKeys.map(key => project(corners[key]))
  return (x, y) => ({ x: a.x + x * (b.x - a.x) + y * (c.x - a.x), y: a.y + x * (b.y - a.y) + y * (c.y - a.y) })
}
export function calibrate(points, baseCorners) {
  if (!Array.isArray(points) || !points.every(validPoint)) throw Error('Bitte jedem Stützpunkt eine Bildposition und gültige Kartenkoordinaten zuordnen.')
  let transform
  if (points.length < 3) {
    const base = baseTransform(baseCorners)
    transform = base
    if (points.length === 1) {
      const p = points[0], from = base(p.x, p.y), to = project(p)
      transform = (x, y) => { const q = base(x, y); return { x: q.x + to.x - from.x, y: q.y + to.y - from.y } }
    } else if (points.length === 2) {
      const [p, q] = points, a = base(p.x, p.y), b = base(q.x, q.y), c = project(p), d = project(q)
      const sx = b.x - a.x, sy = b.y - a.y, tx = d.x - c.x, ty = d.y - c.y
      const denominator = sx * sx + sy * sy
      if (denominator < 1e-8 || tx * tx + ty * ty < 1e-8) throw Error('Die beiden Stützpunkte müssen im Bild und auf der Karte verschieden sein.')
      const real = (sx * tx + sy * ty) / denominator, imaginary = (sx * ty - sy * tx) / denominator
      transform = (x, y) => { const q = base(x, y); return { x: c.x + real * (q.x-a.x) - imaginary * (q.y-a.y), y: c.y + imaginary * (q.x-a.x) + real * (q.y-a.y) } }
    }
  } else {
    // Centred least squares avoids large geographic offsets in the normal equations.
    const targets = points.map(project)
    const mean = values => values.reduce((sum, value) => sum + value, 0) / values.length
    const u = mean(points.map(p => p.x)), v = mean(points.map(p => p.y))
    const x = mean(targets.map(p => p.x)), y = mean(targets.map(p => p.y))
    let uu = 0, uv = 0, vv = 0, ux = 0, vx = 0, uy = 0, vy = 0
    points.forEach((p, i) => {
      const du = p.x-u, dv = p.y-v, dx = targets[i].x-x, dy = targets[i].y-y
      uu += du*du; uv += du*dv; vv += dv*dv
      ux += du*dx; vx += dv*dx; uy += du*dy; vy += dv*dy
    })
    const determinant = uu * vv - uv * uv
    if (determinant <= 1e-12 * (uu + vv) ** 2) throw Error('Die Bildpunkte dürfen nicht alle auf einer Linie liegen oder zusammenfallen.')
    const ax = (ux*vv-vx*uv)/determinant, bx = (vx*uu-ux*uv)/determinant
    const ay = (uy*vv-vy*uv)/determinant, by = (vy*uu-uy*uv)/determinant
    transform = (px, py) => ({ x: x + ax*(px-u) + bx*(py-v), y: y + ay*(px-u) + by*(py-v) })
  }
  const projectedCorners = imageCorners.map(([x, y]) => transform(x, y))
  const [a, b, c] = projectedCorners
  if (Math.abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x)) < 0.5) throw Error('Die Kartenpunkte ergeben keine Fläche. Bitte die Zuordnung prüfen.')
  const corners = Object.fromEntries(cornerKeys.map((key, i) => [key, unproject(projectedCorners[i])]))
  if (!Object.values(corners).every(validLocation)) throw Error('Das ausgerichtete Bild liegt außerhalb des gültigen Kartenbereichs.')
  const residuals = points.map(p => { const predicted = transform(p.x, p.y), actual = project(p); return Math.hypot(predicted.x-actual.x, predicted.y-actual.y) * Math.cos(p.lat*Math.PI/180) })
  return { corners, residuals }
}
