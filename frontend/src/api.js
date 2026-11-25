import axios from 'axios'

// Адрес FastAPI-сервера. Можно переопределить через frontend/.env (VITE_API_URL).
export const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(
  /\/+$/,
  '',
)

export const MAX_FILE_SIZE = 5 * 1024 * 1024
export const ALLOWED_TYPES = ['image/png', 'image/jpeg']

/** Достаёт понятное человеку сообщение из ответа сервера или сетевой ошибки. */
export function getErrorMessage(error) {
  if (axios.isAxiosError(error)) {
    if (error.response) {
      const detail = error.response.data?.detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail)) {
        return detail.map((item) => item.msg || String(item)).join('; ')
      }
      return `Сервер вернул ошибку ${error.response.status}.`
    }
    if (error.code === 'ERR_NETWORK') {
      return `Не удалось связаться с сервером ${API_URL}. Проверьте, что backend запущен.`
    }
    if (error.code === 'ECONNABORTED') {
      return 'Превышено время ожидания ответа сервера.'
    }
    return error.message
  }
  return 'Неизвестная ошибка. Попробуйте ещё раз.'
}

export async function uploadImage(file, onUploadProgress) {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await axios.post(`${API_URL}/api/upload`, formData, {
    onUploadProgress: (event) => {
      const percent = event.total ? Math.round((event.loaded * 100) / event.total) : 0
      console.log(`Загрузка: ${percent}% (${event.loaded} из ${event.total ?? '?'} байт)`)
      onUploadProgress?.(percent)
    },
  })

  return data
}

export async function fetchImages() {
  const { data } = await axios.get(`${API_URL}/api/images`)
  return data
}

export function validateFile(file) {
  if (!file) return 'Файл не выбран.'
  if (!ALLOWED_TYPES.includes(file.type)) {
    return 'Неподдерживаемый формат. Выберите PNG или JPEG.'
  }
  if (file.size > MAX_FILE_SIZE) {
    return 'Файл больше 5 МБ. Выберите изображение меньшего размера.'
  }
  return null
}
