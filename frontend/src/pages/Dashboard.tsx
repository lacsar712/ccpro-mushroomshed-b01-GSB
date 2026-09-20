import { createSignal, onMount, For } from 'solid-js'
import { api } from '../api/client'
import type { DashboardCooling, DashboardStats } from '../types'

export default function Dashboard() {
  const [stats, setStats] = createSignal<DashboardStats | null>(null)
  const [cooling, setCooling] = createSignal<DashboardCooling | null>(null)
  const [error, setError] = createSignal('')

  onMount(() => {
    Promise.all([
      api<DashboardStats>('/api/dashboard/stats'),
      api<DashboardCooling>('/api/dashboard/cooling'),
    ])
      .then(([s, c]) => {
        setStats(s)
        setCooling(c)
      })
      .catch((e) => setError(e.message))
  })

  return (
    <div>
      <header class="page-header">
        <h1>运行看板</h1>
        <p class="muted">出菇室状态 · 冷却 · 近 24h 环境 · 近 7 日采收</p>
      </header>
      {error() && <div class="error">{error()}</div>}
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">菇房总数</div>
          <div class="stat-value">{stats()?.shedTotal ?? '—'}</div>
        </div>
        <div class="stat-card accent">
          <div class="stat-label">出菇中 (fruiting)</div>
          <div class="stat-value">{stats()?.fruitingRoomCount ?? '—'}</div>
        </div>
        <div class="stat-card warn">
          <div class="stat-label">冷却中出菇室</div>
          <div class="stat-value">{cooling()?.total ?? '—'}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">近 24h 环境记录</div>
          <div class="stat-value">{stats()?.climateLast24h ?? '—'}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">近 7 日采收总量 (kg)</div>
          <div class="stat-value">
            {stats() ? stats()!.harvestKgLast7d.toFixed(2) : '—'}
          </div>
        </div>
      </div>

      <section class="panel" style={{ 'margin-top': '20px' }}>
        <h2 style={{ margin: '0 0 12px', 'font-size': '16px' }}>各菇房冷却中室数</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>菇房 ID</th>
                <th>菇房</th>
                <th>冷却中</th>
              </tr>
            </thead>
            <tbody>
              <For each={cooling()?.byShed ?? []}>
                {(s) => (
                  <tr>
                    <td>{s.shedId}</td>
                    <td>{s.shedName}</td>
                    <td>
                      {s.cooling > 0 ? (
                        <span class="badge cooling">{s.cooling}</span>
                      ) : (
                        <span class="muted">0</span>
                      )}
                    </td>
                  </tr>
                )}
              </For>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
