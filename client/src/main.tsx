import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { BenchmarkApp } from './BenchmarkApp.tsx'

const benchmark = new URLSearchParams(location.search).has('benchmark')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {benchmark ? <BenchmarkApp /> : <App />}
  </StrictMode>,
)
