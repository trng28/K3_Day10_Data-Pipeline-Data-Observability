import { useEffect, useState } from 'react'
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Check, CircleDot,
  Database, FlaskConical, Gauge, LoaderCircle, Play, RefreshCw, Save,
  TerminalSquare, Zap,
} from 'lucide-react'

type MetricSet = {
  samples: number
  retrieval_hit_rate: number
  mean_token_f1: number
  judge_accuracy: number
  mean_judge_score: number
}
type Quality = {
  success?: boolean
  passed?: boolean
  passed_checks?: number
  checks_passed?: number
  total_checks?: number
  checks_total?: number
}
type Freshness = { is_fresh: boolean; stale_rows: number; total_rows: number }
type StateData = {
  name: 'baseline' | 'corrupted' | 'repaired'
  metrics: MetricSet | null
  quality: Quality | null
  freshness: Freshness | null
}
type Config = Record<string, string | number | boolean>
type Dashboard = {
  config: Config
  summary: { rawRecords: number; cleanRecords: number }
  states: StateData[]
  steps: Record<string, boolean>
}

const stateMeta = {
  baseline: { label: 'Baseline', hint: 'Clean reference', color: '#77bdd5' },
  corrupted: { label: 'Corrupted', hint: 'Injected failures', color: '#e99185' },
  repaired: { label: 'Repaired', hint: 'Recovered state', color: '#77bda4' },
}
const pct = (value?: number) => value == null ? '—' : `${(value * 100).toFixed(1)}%`
const score = (value?: number) => value == null ? '—' : value.toFixed(2)
const qualityPass = (quality: Quality | null) => quality?.success ?? quality?.passed ?? false

function App() {
  const [data, setData] = useState<Dashboard | null>(null)
  const [config, setConfig] = useState<Config>({})
  const [running, setRunning] = useState<string | null>(null)
  const [consoleOpen, setConsoleOpen] = useState(false)
  const [consoleText, setConsoleText] = useState('Ready. Select a pipeline step to run.')
  const [toast, setToast] = useState<string | null>(null)

  const load = async () => {
    const response = await fetch('/api/dashboard')
    if (!response.ok) throw new Error('Demo API is unavailable')
    const payload = await response.json() as Dashboard
    setData(payload)
    setConfig(payload.config)
  }

  useEffect(() => { load().catch(error => setConsoleText(String(error))) }, [])
  const notify = (message: string) => {
    setToast(message)
    window.setTimeout(() => setToast(null), 2400)
  }
  const saveConfig = async () => {
    const response = await fetch('/api/config', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config),
    })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error)
    setConfig(payload.config)
    notify('Configuration saved')
  }
  const runStep = async (step: string) => {
    setRunning(step)
    setConsoleOpen(true)
    setConsoleText(`Starting ${step}…`)
    try {
      const response = await fetch(`/api/run/${step}`, { method: 'POST' })
      const payload = await response.json()
      setConsoleText(payload.output || payload.error || 'Completed.')
      if (payload.dashboard) {
        setData(payload.dashboard)
        setConfig(payload.dashboard.config)
      }
      if (!response.ok) throw new Error(payload.error || `${step} failed`)
      notify(`${step} completed`)
    } catch (error) {
      setConsoleText(current => `${current}\n\nERROR: ${String(error)}`)
    } finally {
      setRunning(null)
    }
  }

  if (!data) return <div className="loading-screen"><LoaderCircle className="spin"/> Loading…</div>
  const baseline = data.states.find(state => state.name === 'baseline')

  return <div className="compact-app">
    <header className="compact-header">
      <div className="compact-brand"><span><Activity size={18}/></span><div><b>DataFlow</b><small>Pipeline Observatory</small></div></div>
      <div className="header-summary">
        <span><Database/> {data.summary.rawRecords} raw</span>
        <span><Gauge/> {pct(baseline?.metrics?.retrieval_hit_rate)} hit rate</span>
        <i><CircleDot/> Local</i>
        <button onClick={() => load()}><RefreshCw/>Refresh</button>
      </div>
    </header>

    <main className="compact-main">
      <div className="page-title"><div><h1>Pipeline workspace</h1><p>Configure, run and compare the complete data flow.</p></div><span>Python 3.13 · React UI</span></div>

      <section className="workspace-grid">
        <ConfigPanel config={config} setConfig={setConfig} onSave={() => saveConfig().catch(error => notify(String(error)))}/>
        <div className="runner-panel compact-panel">
          <div className="panel-title"><div><small>EXECUTION</small><h2>Run pipeline</h2></div><div className="execution-actions"><button onClick={() => setConsoleOpen(!consoleOpen)}><TerminalSquare/>{consoleOpen ? 'Hide log' : 'View log'}</button><button className="run-all" disabled={Boolean(running)} onClick={() => runStep('all')}>{running === 'all' ? <LoaderCircle className="spin"/> : <Play/>}{running === 'all' ? 'Running all' : 'Run end-to-end'}</button></div></div>
          <div className="compact-flow">
            <RunStep number="1" title="Ingest" detail="Crossref → Raw" icon={<Database/>} done={data.steps.crawl} running={running === 'crawl' || running === 'all'} onRun={() => runStep('crawl')}/>
            <ArrowRight className="step-arrow"/>
            <RunStep number="2" title="Baseline" detail="Clean → Evaluate" icon={<Zap/>} done={data.steps.baseline} running={running === 'baseline' || running === 'all'} onRun={() => runStep('baseline')}/>
            <ArrowRight className="step-arrow"/>
            <RunStep number="3" title="Stress & repair" detail="Corrupt → Recover" icon={<FlaskConical/>} done={data.steps.comparison} running={running === 'comparison' || running === 'all'} onRun={() => runStep('comparison')}/>
          </div>
          {consoleOpen && <div className="compact-console"><div><span/><span/><span/>pipeline://local</div><pre>{consoleText}</pre></div>}
        </div>
      </section>

      <section className="results-panel compact-panel">
        <div className="panel-title"><div><small>RESULTS</small><h2>Baseline vs. corrupted vs. repaired</h2></div><span className="last-state">{data.steps.comparison ? <><Check/> Comparison ready</> : <>Run step 3 to compare</>}</span></div>
        <div className="compact-states">{data.states.map(state => <StateCard key={state.name} state={state} baseline={baseline}/>)}</div>
        <MetricTable states={data.states}/>
      </section>
    </main>
    {toast && <div className="toast"><Check/>{toast}</div>}
  </div>
}

function ConfigPanel({config, setConfig, onSave}: {config: Config; setConfig: (config: Config) => void; onSave: () => void}) {
  const update = (key: string, value: string | number | boolean) => setConfig({...config, [key]: value})
  const sliders = [
    ['CORRUPTION_DROP_RATE', 'Drop'], ['CORRUPTION_BLANK_RATE', 'Blank'],
    ['CORRUPTION_NOISE_RATE', 'Noise'], ['CORRUPTION_STALE_RATE', 'Stale'],
    ['CORRUPTION_DUPLICATE_RATE', 'Duplicate'],
  ]
  return <div className="config-panel compact-panel">
    <div className="panel-title"><div><small>CONFIGURATION</small><h2>Flow settings</h2></div><button className="save-config" onClick={onSave}><Save/>Save</button></div>
    <div className="core-fields">
      <label><span>Provider</span><select value={String(config.LLM_PROVIDER ?? '')} onChange={e => update('LLM_PROVIDER', e.target.value)}><option value="gemini">Gemini</option><option value="openai">OpenAI</option><option value="anthropic">Anthropic</option><option value="openrouter">OpenRouter</option><option value="ollama">Ollama</option><option value="custom">Custom</option></select></label>
      <label className="wide"><span>Model</span><input value={String(config.LLM_MODEL ?? '')} onChange={e => update('LLM_MODEL', e.target.value)}/></label>
      <label><span>Embedding</span><select value={String(config.EMBEDDING_PROVIDER ?? 'openai')} onChange={e => update('EMBEDDING_PROVIDER', e.target.value)}><option value="openai">OpenAI</option><option value="local">Local</option></select></label>
      <label className="wide"><span>Embedding model</span><input value={String(config.EMBEDDING_MODEL ?? 'text-embedding-3-small')} onChange={e => update('EMBEDDING_MODEL', e.target.value)}/></label>
      <label><span>Top-k</span><input type="number" value={Number(config.TOP_K ?? 4)} onChange={e => update('TOP_K', Number(e.target.value))}/></label>
      <label><span>Records</span><input type="number" value={Number(config.MAX_RESULTS ?? 100)} onChange={e => update('MAX_RESULTS', Number(e.target.value))}/></label>
      <label className="query"><span>Crossref query</span><input value={String(config.SOURCE_QUERY ?? '')} onChange={e => update('SOURCE_QUERY', e.target.value)}/></label>
    </div>
    <div className="config-divider"><span>Corruption intensity</span><i/></div>
    <div className="slider-grid">{sliders.map(([key, label]) => <label key={key}><span>{label}<b>{Math.round(Number(config[key] ?? 0) * 100)}%</b></span><input type="range" min="0" max="0.5" step="0.01" value={Number(config[key] ?? 0)} onChange={e => update(key, Number(e.target.value))}/></label>)}</div>
    <div className="inline-flags">
      {[['REFRESH_SOURCE', 'Refresh source'], ['REFRESH_TEST_SET', 'New test set'], ['RUN_RAGAS', 'Ragas']].map(([key, label]) => <label key={key}><input type="checkbox" checked={Boolean(config[key])} onChange={e => update(key, e.target.checked)}/><i/><span>{label}</span></label>)}
    </div>
  </div>
}

function RunStep({number, title, detail, icon, done, running, onRun}: {number: string; title: string; detail: string; icon: React.ReactNode; done: boolean; running: boolean; onRun: () => void}) {
  return <div className={`compact-step ${done ? 'done' : ''}`}><div className="step-heading"><span>{icon}</span><i>{number}</i>{done && <Check className="step-check"/>}</div><b>{title}</b><small>{detail}</small><button disabled={running} onClick={onRun}>{running ? <LoaderCircle className="spin"/> : <Play/>}{running ? 'Running' : 'Run'}</button></div>
}

function StateCard({state, baseline}: {state: StateData; baseline?: StateData}) {
  const meta = stateMeta[state.name]
  const baseHit = baseline?.metrics?.retrieval_hit_rate
  const delta = state.metrics && baseHit != null ? state.metrics.retrieval_hit_rate - baseHit : null
  const passed = state.quality?.passed_checks ?? state.quality?.checks_passed ?? 0
  const total = state.quality?.total_checks ?? state.quality?.checks_total ?? 0
  return <article className="compact-state" style={{'--state': meta.color} as React.CSSProperties}>
    <div className="compact-state-head"><span><i/>{meta.label}<small>{meta.hint}</small></span>{state.metrics ? <b>Ready</b> : <em>Pending</em>}</div>
    <div className="state-hit"><strong>{pct(state.metrics?.retrieval_hit_rate)}</strong><span>Retrieval hit rate</span>{delta != null && state.name !== 'baseline' && <i className={delta < 0 ? 'down' : 'up'}>{delta < 0 ? <ArrowDownRight/> : <ArrowUpRight/>}{delta >= 0 ? '+' : ''}{(delta * 100).toFixed(1)} pts</i>}</div>
    <div className="state-signals"><span>Token F1 <b>{score(state.metrics?.mean_token_f1)}</b></span><span>Judge <b>{pct(state.metrics?.judge_accuracy)}</b></span><span>Quality <b className={qualityPass(state.quality) ? 'pass' : 'fail'}>{state.quality ? `${passed}/${total}` : '—'}</b></span><span>Stale <b>{state.freshness?.stale_rows ?? '—'}</b></span></div>
  </article>
}

function MetricTable({states}: {states: StateData[]}) {
  const rows = [
    ['Retrieval hit', 'retrieval_hit_rate', 1], ['Token F1', 'mean_token_f1', 1],
    ['Judge accuracy', 'judge_accuracy', 1], ['Judge score', 'mean_judge_score', 5],
  ] as const
  return <div className="compact-metrics"><div className="metrics-head"><span>Metric</span>{states.map(state => <span key={state.name}>{stateMeta[state.name].label}</span>)}</div>{rows.map(([label, key, max]) => <div className="metrics-row" key={key}><b>{label}</b>{states.map(state => {const value = state.metrics?.[key]; return <div key={state.name}><i><span style={{width: `${((value ?? 0) / max) * 100}%`, background: stateMeta[state.name].color}}/></i><em>{value == null ? '—' : key === 'mean_judge_score' ? value.toFixed(2) : pct(value)}</em></div>})}</div>)}</div>
}

export default App
