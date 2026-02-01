import { useState, useEffect, useRef, useCallback } from 'react'
import {
  health,
  listPresetVideos,
  getPresetVideoUrl,
  uploadVideo,
  transcribe,
  listInsights,
  acknowledgeInsight,
  analyzeSession,
} from './api'
import './App.css'

function App() {
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID())
  const [presetList, setPresetList] = useState([])
  const [videoSource, setVideoSource] = useState('preset') // preset | upload | record
  const [presetFile, setPresetFile] = useState('')
  const [uploadedFile, setUploadedFile] = useState(null)
  const [recordedBlob, setRecordedBlob] = useState(null)
  const [videoUrl, setVideoUrl] = useState('')
  const [transcript, setTranscript] = useState({ full_text: '', segments: [] })
  const [insights, setInsights] = useState([])
  const [vitals, setVitals] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const recorderRef = useRef(null)

  useEffect(() => {
    health().catch(() => setError('Backend not running. Start: cd backend && uvicorn app.main:app --reload'))
    listPresetVideos().then(setPresetList).catch(() => setPresetList([]))
  }, [])

  useEffect(() => {
    if (videoSource === 'preset' && presetFile) {
      setVideoUrl(getPresetVideoUrl(presetFile))
    } else if (videoSource === 'upload' && uploadedFile) {
      const u = URL.createObjectURL(uploadedFile)
      setVideoUrl(u)
      return () => URL.revokeObjectURL(u)
    } else if (videoSource === 'record' && recordedBlob) {
      const u = URL.createObjectURL(recordedBlob)
      setVideoUrl(u)
      return () => URL.revokeObjectURL(u)
    } else {
      setVideoUrl('')
    }
  }, [videoSource, presetFile, uploadedFile, recordedBlob])

  const refreshInsights = useCallback(() => {
    listInsights(sessionId).then((d) => setInsights(d.insights || [])).catch(() => setInsights([]))
  }, [sessionId])

  useEffect(() => {
    refreshInsights()
  }, [sessionId, refreshInsights])

  const handleUpload = (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    setUploadedFile(f)
    setError('')
    setTranscript({ full_text: '', segments: [] })
    setSessionId(crypto.randomUUID())
  }

  const startRecording = async () => {
    setError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      streamRef.current = stream
      const recorder = new MediaRecorder(stream)
      recorderRef.current = recorder
      const chunks = []
      recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data)
      recorder.onstop = () => {
        setRecordedBlob(new Blob(chunks, { type: 'video/webm' }))
        stream.getTracks().forEach((t) => t.stop())
      }
      recorder.start(1000)
      setVideoSource('record')
    } catch (err) {
      setError('Camera/mic access denied or not available.')
    }
  }

  const stopRecording = () => {
    if (recorderRef.current?.state === 'recording') {
      recorderRef.current.stop()
    }
  }

  const runAnalysis = async () => {
    setAnalyzing(true)
    setError('')
    try {
      let usePreset = ''
      let videoPath = ''
      if (videoSource === 'preset' && presetFile) {
        usePreset = presetFile
      } else if (videoSource === 'upload' && uploadedFile) {
        const form = new FormData()
        form.append('file', uploadedFile)
        form.append('session_id', sessionId)
        const up = await fetch('/api/upload-video', { method: 'POST', body: form })
        if (!up.ok) throw new Error(await up.text())
        const data = await up.json()
        videoPath = data.stored_filename || data.filename || ''
      } else if (videoSource === 'record' && recordedBlob) {
        const file = new File([recordedBlob], 'recorded.webm', { type: 'video/webm' })
        const form = new FormData()
        form.append('file', file)
        form.append('session_id', sessionId)
        const up = await fetch('/api/upload-video', { method: 'POST', body: form })
        if (!up.ok) throw new Error(await up.text())
        const data = await up.json()
        videoPath = data.stored_filename || 'recorded.webm'
      }
      const result = await analyzeSession(sessionId, { use_preset: usePreset || undefined, video_path: videoPath || undefined })
      setTranscript({ full_text: result.full_text || '', segments: result.segments || [] })
      setInsights(result.insights || [])
      setVitals(result.vitals || null)
    } catch (err) {
      setError(err.message || 'Analysis failed.')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleAck = async (insightId) => {
    try {
      await acknowledgeInsight(sessionId, insightId)
      refreshInsights()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>PrePsych</h1>
        <p className="tagline">Therapy copilot — Presage vitals + Whisper + Ollama (local)</p>
      </header>

      {error && (
        <div className="banner error">
          {error}
        </div>
      )}

      <section className="video-section">
        <div className="tabs">
          <button
            className={videoSource === 'preset' ? 'active' : ''}
            onClick={() => setVideoSource('preset')}
          >
            Preset video
          </button>
          <button
            className={videoSource === 'upload' ? 'active' : ''}
            onClick={() => setVideoSource('upload')}
          >
            Upload
          </button>
          <button
            className={videoSource === 'record' ? 'active' : ''}
            onClick={() => setVideoSource('record')}
          >
            Record
          </button>
        </div>

        {videoSource === 'preset' && (
          <div className="preset-select">
            <label>Preset:</label>
            <select
              value={presetFile}
              onChange={(e) => { setPresetFile(e.target.value); setTranscript({ full_text: '', segments: [] }) }}
            >
              <option value="">Select a preset video</option>
              {presetList.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
            {presetList.length === 0 && (
              <span className="hint">Add videos to backend/preset_videos/</span>
            )}
          </div>
        )}

        {videoSource === 'upload' && (
          <div className="upload-zone">
            <input
              type="file"
              accept="video/*"
              onChange={handleUpload}
              id="video-upload"
            />
            <label htmlFor="video-upload">
              {uploadedFile ? uploadedFile.name : 'Choose video file'}
            </label>
          </div>
        )}

        {videoSource === 'record' && (
          <div className="record-zone">
            {!recorderRef.current || recorderRef.current?.state !== 'recording' ? (
              <button className="btn primary" onClick={startRecording}>
                Start recording
              </button>
            ) : (
              <button className="btn danger" onClick={stopRecording}>
                Stop recording
              </button>
            )}
            {recordedBlob && <span className="recorded-hint">Recorded. Click Analyze below.</span>}
          </div>
        )}

        {videoUrl && (
          <div className="player-wrap">
            <video ref={videoRef} src={videoUrl} controls className="video-player" />
          </div>
        )}

        <div className="analyze-row">
          <button
            className="btn primary large"
            onClick={runAnalysis}
            disabled={analyzing || (!presetFile && !uploadedFile && !recordedBlob)}
          >
            {analyzing ? 'Analyzing…' : 'Transcribe & generate insights'}
          </button>
        </div>
      </section>

      {vitals && (
        <section className="vitals-banner">
          <strong>Vitals</strong> (Presage {vitals.source})
          {vitals.heart_rate_bpm != null && ` · HR ${vitals.heart_rate_bpm} BPM`}
          {vitals.breathing_bpm != null && ` · Breathing ${vitals.breathing_bpm} BPM`}
        </section>
      )}

      <div className="content-grid">
        <section className="transcript-panel">
          <h2>Transcription</h2>
          {transcript.full_text ? (
            <div className="transcript-text">{transcript.full_text}</div>
          ) : (
            <p className="muted">Transcription will appear after analysis.</p>
          )}
        </section>

        <section className="insights-panel">
          <h2>Copilot insights</h2>
          <p className="muted">Bubbles from Ollama (local). Check when addressed.</p>
          <div className="insights-list">
            {insights.map((i) => (
              <div
                key={i.id}
                className={`insight-bubble ${i.status === 'acknowledged' ? 'acknowledged' : ''}`}
              >
                <p className="insight-text">{i.text}</p>
                {i.trigger_context && (
                  <span className="insight-context">{i.trigger_context}</span>
                )}
                {i.status === 'pending' && (
                  <button
                    className="btn check"
                    onClick={() => handleAck(i.id)}
                    title="Mark as addressed"
                  >
                    ✓
                  </button>
                )}
                {i.status === 'acknowledged' && (
                  <span className="ack-label">Addressed</span>
                )}
              </div>
            ))}
          </div>
          {insights.length === 0 && (
            <p className="muted">No insights yet. Run analysis on a video.</p>
          )}
        </section>
      </div>

      <footer className="footer">
        Presage vitals (mock or from iOS) + Whisper transcription + Ollama — all local for privacy.
      </footer>
    </div>
  )
}

export default App
