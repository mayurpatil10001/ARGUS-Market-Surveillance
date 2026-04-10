import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from 'react-query'
import { Toaster } from 'react-hot-toast'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import LiveAlerts from './pages/LiveAlerts'
import AccountDNA from './pages/AccountDNA'
import NetworkView from './pages/NetworkView'
import CaseBuilder from './pages/CaseBuilder'
import WeeklySummary from './pages/WeeklySummary'
import MitigationCenter from './pages/MitigationCenter'
import PS402Signals from './pages/PS402Signals'

const qc = new QueryClient({
  defaultOptions: { queries: { refetchInterval: 30000, retry: 1, refetchOnWindowFocus: false } },
})

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <div style={{ display:'flex', minHeight:'100vh', background:'var(--bg-base)' }}>
          <Sidebar />
          <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
            <TopBar />
            <main style={{ flex:1, overflow:'auto', padding:'24px' }}>
              <Routes>
                <Route path="/" element={<Navigate to="/alerts" replace />} />
                <Route path="/alerts" element={<LiveAlerts />} />
                <Route path="/dna" element={<AccountDNA />} />
                <Route path="/network" element={<NetworkView />} />
                <Route path="/cases" element={<CaseBuilder />} />
                <Route path="/summary" element={<WeeklySummary />} />
                <Route path="/mitigation" element={<MitigationCenter />} />
                <Route path="/ps402" element={<PS402Signals />} />
              </Routes>
            </main>
          </div>
        </div>
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: 'var(--bg-card)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-bright)',
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              borderRadius: '2px',
            },
          }}
        />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
