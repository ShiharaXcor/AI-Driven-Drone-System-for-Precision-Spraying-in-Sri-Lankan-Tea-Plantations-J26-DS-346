import { useEffect, useState } from 'react'
import api from '../../utils/api'

function DetectionPage() {
  const [status, setStatus] = useState('checking...')

  useEffect(() => {
    api.get('/c1/health')
      .then((res) => setStatus(res.data.status))
      .catch(() => setStatus('backend not reachable'))
  }, [])

  return (
    <section>
      <h2>C1 - Spray detection</h2>
      <p>Backend status: {status}</p>
    </section>
  )
}

export default DetectionPage