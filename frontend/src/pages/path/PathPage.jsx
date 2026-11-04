import { useEffect, useState } from 'react'
import api from '../../utils/api'

function PathPage() {
  const [status, setStatus] = useState('checking...')

  useEffect(() => {
    api.get('/c3/health')
      .then((res) => setStatus(res.data.status))
      .catch(() => setStatus('backend not reachable'))
  }, [])

  return (
    <section>
      <h2>C3 - Smart path</h2>
      <p>Backend status: {status}</p>
    </section>
  )
}

export default PathPage