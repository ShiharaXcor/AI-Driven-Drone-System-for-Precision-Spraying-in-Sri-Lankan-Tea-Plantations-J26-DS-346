import api from '../../utils/api'

// Turn backend errors into a readable message (like the old api.js did)
const unwrap = (request) =>
  request
    .then((res) => res.data)
    .catch((err) => {
      const detail = err.response?.data?.detail
      throw new Error(typeof detail === 'string' ? detail : err.message)
    })

export const getRecommendation = (inputs) => unwrap(api.post('/c2/recommend', inputs))
export const getDriftCurve = (inputs) => unwrap(api.post('/c2/drift-curve', inputs))
export const getWeather = (region) => unwrap(api.get(`/c2/weather/${encodeURIComponent(region)}`))
export const simulateMission = (inputs) => unwrap(api.post('/c2/mission/simulate', inputs))