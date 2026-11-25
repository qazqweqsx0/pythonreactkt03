import { useCallback, useEffect, useRef, useState } from 'react'
import {
  API_URL,
  fetchImages,
  getErrorMessage,
  uploadImage,
  validateFile,
} from './api'

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`
  return `${(bytes / (1024 * 1024)).toFixed(2)} МБ`
}

export default function App() {
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [progress, setProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [history, setHistory] = useState([])
  const fileInputRef = useRef(null)
  const previewUrlRef = useRef('')

  // Локальный предпросмотр через URL.createObjectURL до отправки на сервер.
  const setLocalPreview = useCallback((selected) => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current)
    }
    const url = selected ? URL.createObjectURL(selected) : ''
    previewUrlRef.current = url
    setPreviewUrl(url)
  }, [])

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
    }
  }, [])

  const loadHistory = useCallback(async () => {
    try {
      setHistory(await fetchImages())
    } catch {
      // История не критична для работы формы — не показываем ошибку.
    }
  }, [])

  useEffect(() => {
    loadHistory()
  }, [loadHistory])

  const handleSelect = (event) => {
    const selected = event.target.files?.[0] ?? null
    setError('')
    setResult(null)
    setProgress(0)

    const validationError = validateFile(selected)
    if (validationError) {
      setFile(null)
      setLocalPreview(null)
      setError(validationError)
      return
    }

    setFile(selected)
    setLocalPreview(selected)
  }

  const handleUpload = async (event) => {
    event.preventDefault()
    if (!file || uploading) return

    const validationError = validateFile(file)
    if (validationError) {
      setError(validationError)
      return
    }

    setUploading(true)
    setError('')
    setResult(null)
    setProgress(0)

    try {
      const data = await uploadImage(file, setProgress)
      setProgress(100)
      setResult(data)
      setFile(null)
      setLocalPreview(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      loadHistory()
    } catch (uploadError) {
      setError(getErrorMessage(uploadError))
    } finally {
      setUploading(false)
    }
  }

  const handleReset = () => {
    setFile(null)
    setLocalPreview(null)
    setResult(null)
    setError('')
    setProgress(0)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div className="page">
      <header className="hero">
        <h1>Загрузка изображений</h1>
        <p>
          FastAPI + Pillow + StaticFiles &nbsp;→&nbsp; React + Axios + FormData
        </p>
        <span className="api-url">API: {API_URL}</span>
      </header>

      <main className="grid">
        <section className="card">
          <h2>1. Выбор и отправка</h2>

          <form onSubmit={handleUpload}>
            <label className="dropzone">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg"
                onChange={handleSelect}
                disabled={uploading}
              />
              <span className="dropzone-title">
                {file ? file.name : 'Выберите PNG или JPEG'}
              </span>
              <span className="dropzone-hint">
                {file ? formatSize(file.size) : 'максимум 5 МБ'}
              </span>
            </label>

            <div className="preview">
              {previewUrl ? (
                <>
                  <img src={previewUrl} alt="Локальный предпросмотр" />
                  <span className="preview-caption">Предпросмотр (до загрузки)</span>
                </>
              ) : (
                <div className="preview-empty">Здесь появится предпросмотр</div>
              )}
            </div>

            <div className="actions">
              <button type="submit" disabled={!file || uploading}>
                {uploading ? 'Загрузка…' : 'Загрузить на сервер'}
              </button>
              <button
                type="button"
                className="secondary"
                onClick={handleReset}
                disabled={uploading || (!file && !result && !error)}
              >
                Сбросить
              </button>
            </div>
          </form>

          {(uploading || progress > 0) && (
            <div className="progress-block" aria-live="polite">
              <div className="progress-head">
                <span>Прогресс загрузки</span>
                <strong>{progress}%</strong>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}

          {error && (
            <div className="alert error" role="alert">
              <strong>Ошибка</strong>
              <span>{error}</span>
            </div>
          )}
        </section>

        <section className="card">
          <h2>2. Результат на сервере</h2>

          {result ? (
            <div className="result">
              <img
                className="thumb"
                src={result.thumbnail_url}
                alt={`Миниатюра ${result.filename}`}
              />
              <dl>
                <dt>Файл</dt>
                <dd>{result.filename}</dd>
                <dt>Размер</dt>
                <dd>
                  {formatSize(result.size)} · {result.width}×{result.height}
                </dd>
                <dt>Миниатюра</dt>
                <dd>
                  <a href={result.thumbnail_url} target="_blank" rel="noreferrer">
                    {result.thumbnail_url}
                  </a>
                </dd>
                <dt>Оригинал</dt>
                <dd>
                  <a href={result.original_url} target="_blank" rel="noreferrer">
                    {result.original_url}
                  </a>
                </dd>
              </dl>
            </div>
          ) : (
            <div className="placeholder">
              Загрузите изображение — сервер создаст миниатюру через Pillow и вернёт
              полный URL.
            </div>
          )}

          {history.length > 0 && (
            <div className="history">
              <h3>Загружено ранее</h3>
              <ul>
                {history.slice(0, 8).map((item) => (
                  <li key={item.id}>
                    <img src={item.thumbnail_url} alt={item.filename} />
                    <a href={item.original_url} target="_blank" rel="noreferrer">
                      {item.filename}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </main>

      <footer className="footer">
        Валидация: только PNG/JPEG, до 5 МБ · Миниатюра 320×320 с сохранением
        пропорций
      </footer>
    </div>
  )
}
