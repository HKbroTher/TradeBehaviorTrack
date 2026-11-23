import { useEffect, useState } from 'react'
import { invoke } from '@tauri-apps/api/core'
import './App.css'

function App() {
  const [consent, setConsent] = useState(false)
  const [message, setMessage] = useState('正在读取设置…')

  useEffect(() => {
    invoke<boolean>('get_consent').then((enabled) => {
      setConsent(enabled)
      setMessage('Windows 输入采集尚未接入；当前不会记录键鼠数据。')
    }).catch(() => setMessage('请在 Tauri 桌面程序中打开此页面。'))
  }, [])

  async function changeConsent(enabled: boolean) {
    try {
      setConsent(await invoke<boolean>('set_consent', { enabled }))
      setMessage('Windows 输入采集尚未接入；当前不会记录键鼠数据。')
    } catch {
      setMessage('无法保存设置，请在桌面程序中重试。')
    }
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
      <p role="status">{message}</p>
    </section>
    <section aria-labelledby="status-title"><h2 id="status-title">当前状态</h2><strong>尚未开始采集</strong>
      <p>检测核心与模拟数据流程已建立；Windows 实时采集及通知仍在开发中。</p></section>
  </main>
}

export default App
