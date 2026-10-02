const csrf = () =>
  document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith('csrftoken='))
    ?.split('=')[1]

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
    this.code = data?.code || (status === 401 ? 'not_authenticated' : status === 403 ? 'permission_denied' : 'request_failed')
  }
}

function errorMessage(data, status) {
  const detail = typeof data.detail === 'string' ? data.detail : ''
  if (status === 401) return 'Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.'
  if (status === 403 && /authentication credentials were not provided|authentifizierungsdaten wurden nicht bereitgestellt/i.test(detail)) {
    return 'Bitte melden Sie sich an, um diese Aktion auszuführen.'
  }
  if (status === 403 && /you do not have permission to perform this action|sie sind nicht berechtigt, diese aktion durchzuführen/i.test(detail)) {
    return 'Sie haben keine Berechtigung für diese Aktion. Bitte lassen Sie Ihre Gruppenmitgliedschaft und Rechte prüfen.'
  }
  if (detail) return detail
  const firstError = Object.values(data)
    .flat(Infinity)
    .find((value) => typeof value === 'string' && value)
  if (firstError) return firstError
  if (status === 403) return 'Sie haben keine Berechtigung für diese Aktion. Bitte lassen Sie Ihre Gruppenmitgliedschaft und Rechte prüfen.'
  if (status >= 500) return 'Der Server konnte die Anfrage nicht verarbeiten. Bitte später erneut versuchen.'
  return 'Anfrage fehlgeschlagen. Bitte Eingaben prüfen und erneut versuchen.'
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
  const data = (await response.json().catch(() => ({}))) || {}
  if (!response.ok) throw new ApiError(errorMessage(data, response.status), response.status, data)
  return data
}

export function logout() {
  // A browser navigation lets OIDCLogoutView redirect to the provider with its cookies.
  const form = document.createElement('form')
  form.method = 'POST'
  form.action = '/api/auth/logout/'
  const token = document.createElement('input')
  token.type = 'hidden'
  token.name = 'csrfmiddlewaretoken'
  token.value = decodeURIComponent(csrf() || '')
  form.appendChild(token)
  document.body.appendChild(form)
  form.submit()
}
