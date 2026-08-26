// Realtime voice dispatch to the CEO — mic capture -> backend WebSocket
// relay (app/api/voice.py) -> Vertex AI Live API -> streamed audio back.
// See that module's docstring for why the browser only ever holds a PCM
// audio stream, never a credential.
//
// ponytail: uses ScriptProcessorNode (deprecated in favor of AudioWorklet)
// for mic capture — simpler (no separate worklet module to load/serve),
// still supported everywhere. Upgrade to AudioWorklet if the deprecation
// warning ever becomes a real problem.

import { useRef, useState } from 'react'
import { Icon } from './Icon'
import { getIdToken } from '../lib/authClient'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000'

function wsUrl(orgId: string, token: string): string {
  const base = BACKEND_URL.replace(/^http/, 'ws')
  return `${base}/ws/voice/${orgId}?token=${encodeURIComponent(token)}`
}

function floatToPcm16(input: Float32Array): ArrayBuffer {
  const out = new Int16Array(input.length)
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]))
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff
  }
  return out.buffer
}

function arrayBufferToBase64(buf: ArrayBuffer): string {
  let binary = ''
  const bytes = new Uint8Array(buf)
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i])
  return btoa(binary)
}

function base64ToArrayBuffer(b64: string): ArrayBuffer {
  const binary = atob(b64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes.buffer
}

type VoiceState = 'idle' | 'connecting' | 'live' | 'error'

export function VoicePanel({ orgId }: { orgId: string }) {
  const [state, setState] = useState<VoiceState>('idle')
  const wsRef = useRef<WebSocket | null>(null)
  const micContextRef = useRef<AudioContext | null>(null)
  const playbackContextRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const playbackCursorRef = useRef(0)

  async function start() {
    setState('connecting')
    try {
      const token = await getIdToken()
      if (!token) throw new Error('not signed in')

      const ws = new WebSocket(wsUrl(orgId, token))
      wsRef.current = ws

      const playbackContext = new AudioContext({ sampleRate: 24000 })
      playbackContextRef.current = playbackContext
      playbackCursorRef.current = playbackContext.currentTime

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data) as { type: string; data: string }
        if (message.type !== 'audio') return
        const pcm = new Int16Array(base64ToArrayBuffer(message.data))
        const buffer = playbackContext.createBuffer(1, pcm.length, 24000)
        const channel = buffer.getChannelData(0)
        for (let i = 0; i < pcm.length; i++) channel[i] = pcm[i] / 0x8000
        const source = playbackContext.createBufferSource()
        source.buffer = buffer
        source.connect(playbackContext.destination)
        const startAt = Math.max(playbackContext.currentTime, playbackCursorRef.current)
        source.start(startAt)
        playbackCursorRef.current = startAt + buffer.duration
      }

      ws.onerror = () => setState('error')
      ws.onclose = () => setState('idle')

      await new Promise<void>((resolve, reject) => {
        ws.onopen = () => resolve()
        setTimeout(() => reject(new Error('connect timeout')), 8000)
      })

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const micContext = new AudioContext({ sampleRate: 16000 })
      micContextRef.current = micContext
      const source = micContext.createMediaStreamSource(stream)
      const processor = micContext.createScriptProcessor(4096, 1, 1)
      processor.onaudioprocess = (e) => {
        if (ws.readyState !== WebSocket.OPEN) return
        const pcm = floatToPcm16(e.inputBuffer.getChannelData(0))
        ws.send(JSON.stringify({ type: 'audio', data: arrayBufferToBase64(pcm) }))
      }
      source.connect(processor)
      processor.connect(micContext.destination)

      setState('live')
    } catch {
      setState('error')
      stop()
    }
  }

  function stop() {
    wsRef.current?.send(JSON.stringify({ type: 'end' }))
    wsRef.current?.close()
    wsRef.current = null
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    void micContextRef.current?.close()
    micContextRef.current = null
    void playbackContextRef.current?.close()
    playbackContextRef.current = null
    setState('idle')
  }

  return (
    <button
      className="corp-tip"
      data-tip={state === 'live' ? 'End voice call with the CEO' : 'Talk to the CEO'}
      onClick={() => (state === 'live' || state === 'connecting' ? stop() : start())}
      style={{
        width: 28,
        height: 28,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: state === 'live' ? 'var(--corp-coral)' : 'var(--corp-paper-100)',
        boxShadow: 'inset 0 0 0 1px var(--corp-ink-300)',
        border: 'none',
        cursor: 'pointer',
        color: 'var(--corp-ink-900)',
      }}
    >
      <Icon name="mic" />
    </button>
  )
}
