import { useEffect, useState } from 'react'
import api from '../../utils/api'

function WindPage() {
  const [status, setStatus] = useState('checking...')

  useEffect(() => {
    api.get('/c2/health')
      .then((res) => setStatus(res.data.status))
      .catch(() => setStatus('backend not reachable'))
  }, [])

  return (
    <section>
      <h2>C2 - Wind handling</h2>
      <p>Backend status: {status}</p>
    </section>
  )
}

export default WindPage