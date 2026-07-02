import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { BenchmarkApp } from './BenchmarkApp.tsx'
import { DBProvider } from './hooks/useDB.tsx'

const benchmark = new URLSearchParams(location.search).has('benchmark')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DBProvider>
      {benchmark ? <BenchmarkApp /> : <App />}
    </DBProvider>
  </StrictMode>,
)
