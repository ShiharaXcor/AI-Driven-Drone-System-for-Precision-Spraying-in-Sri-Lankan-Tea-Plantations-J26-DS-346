import axios from 'axios'

// One shared connection to the backend for the whole frontend.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 10000,
})

export default api