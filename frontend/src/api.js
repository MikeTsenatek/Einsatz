const csrf = () =>
  document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith('csrftoken='))
    ?.split('=')[1]

function errorMessage(data) {
  if (data.detail) return data.detail
  const firstError = Object.values(data).flat().find(Boolean)
  return firstError || 'Anfrage fehlgeschlagen'
}

export async function api(path, options = {}) {
  const headers = { Accept: 'application/json', ...options.headers }
  if (options.body) headers['Content-Type'] = 'application/json'
  if (csrf()) headers['X-CSRFToken'] = decodeURIComponent(csrf())

  const response = await fetch('/api' + path, {
    credentials: 'same-origin',
    ...options,
    headers,
  })

  if (response.status === 204) return
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(errorMessage(data))
  return data
}
