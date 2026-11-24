import { useEffect, useState } from 'react'
import { invoke } from '@tauri-apps/api/core'
import './App.css'

type Alert = { id: number; at: string; score: number; reasons: { metric: string; robust_z: number }[]; feedback: string | null }
type Dashboard = { windows: number; days: number; latest_score: number | null; alerts: Alert[] }

function App() {
  const [consent, setConsent] = useState(false)
  const [message, setMessage] = useState('正在读取设置…')
  const [data, setData] = useState<Dashboard | null>(null)

  async function refresh() {
    try { setData(await invoke<Dashboard>('dashboard')) }
    catch { setMessage('暂时无法读取本地数据。') }
  }

  useEffect(() => {
    invoke<boolean>('get_consent').then((enabled) => {
      setConsent(enabled)
      setMessage('Windows 输入采集尚未接入；当前不会记录键鼠数据。')
    }).catch(() => setMessage('请在 Tauri 桌面程序中打开此页面。'))
    void refresh()
    const timer = window.setInterval(() => void refresh(), 10000)
    return () => window.clearInterval(timer)
  }, [])

  async function changeConsent(enabled: boolean) {
    try {
      setConsent(await invoke<boolean>('set_consent', { enabled }))
      setMessage('Windows 输入采集尚未接入；当前不会记录键鼠数据。')
    } catch {
      setMessage('无法保存设置，请在桌面程序中重试。')
    }
  }

  async function giveFeedback(id: number, choice: string) {
    try { await invoke('set_feedback', { alertId: id, choice }); await refresh() }
    catch { setMessage('反馈保存失败，请重试。') }
  }

  async function deleteData() {
    if (!window.confirm('确定删除全部本地行为窗口、基线样本和提醒记录吗？')) return
    try { await invoke('delete_personal_data'); await refresh(); setMessage('本地个人数据已删除。') }
    catch { setMessage('删除失败，请先停止独立采集程序并重试。') }
  }

  async function pause() {
    try { await invoke('pause_monitoring'); setConsent(false); setMessage('已向独立采集程序发送暂停信号。') }
    catch { setMessage('暂停失败，请直接停止独立采集程序。') }
  }

  return <main>
    <header><span className="eyebrow">BEHAVIORAL GUARD</span><h1>行为监测设置</h1>
      <p>未来将依据你自己的操作基线，提醒持续而明显的行为变化。</p></header>
    <section aria-labelledby="privacy-title">
      <h2 id="privacy-title">采集范围与隐私</h2>
      <p>计划仅在本机统计鼠标移动、点击及键盘输入的时间节奏。不会保存输入文字、密码、剪贴板或屏幕内容。</p>
      <p>异常分数仅表示相对个人常态的偏离，不代表心理状态或医学风险。</p>
    </section>
    <section aria-labelledby="consent-title">
      <h2 id="consent-title">授权</h2>
      <label className="toggle"><input type="checkbox" checked={consent} onChange={(event) => changeConsent(event.target.checked)} />
        我了解上述范围，并授权在采集功能完成后启用监测</label>
      <p>此设置仅在当前桌面程序运行期间有效；独立采集程序需要单独启动和授权。</p>
      <button type="button" onClick={pause}>暂停监测</button>
      <p role="status">{message}</p>
    </section>
    <section aria-labelledby="status-title"><h2 id="status-title">本地数据</h2>
      <p>有效学习日期：{data?.days ?? '—'} / 7　窗口数：{data?.windows ?? '—'}　最近提醒分数：{data?.latest_score ?? '—'}</p>
      <p>桌面程序不会自动开始采集。Windows 鼠标采集原型需独立运行。</p>
      <button type="button" onClick={deleteData}>删除全部个人数据</button>
    </section>
    <section aria-labelledby="alerts-title"><h2 id="alerts-title">最近提醒</h2>
      {data?.alerts.length ? <ul>{data.alerts.map((alert) => <li key={alert.id}>
        <strong>{alert.score} / 100</strong>　{alert.at}<br />
        主要偏离：{alert.reasons.slice(0, 3).map((reason) => `${reason.metric} (${reason.robust_z})`).join('、') || '—'}<br />
        {alert.feedback ? `反馈：${alert.feedback}` : <span className="actions">
          <button onClick={() => giveFeedback(alert.id, 'ignore')}>忽略</button>
          <button onClick={() => giveFeedback(alert.id, 'normal')}>正常操作</button>
          <button onClick={() => giveFeedback(alert.id, 'fatigue_or_emotion')}>状态变化</button>
          <button onClick={() => giveFeedback(alert.id, 'device_or_environment')}>设备或环境变化</button>
        </span>}
      </li>)}</ul> : <p>暂无提醒记录。</p>}
    </section>
  </main>
}

export default App
