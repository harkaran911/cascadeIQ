import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

export const fetchZones = () => api.get('/zones/').then(r => r.data);
export const fetchIncidents = () => api.get('/incidents/').then(r => r.data);
export const fetchResources = () => api.get('/resources/').then(r => r.data);
export const fetchDeployments = () => api.get('/resources/deployments').then(r => r.data);
export const fetchCascade = () => api.get('/optimizer/cascade').then(r => r.data);
export const fetchDirectives = () => api.get('/optimizer/directives').then(r => r.data);
export const runOptimizer = () => api.post('/optimizer/run').then(r => r.data);
export const approveDeployment = (id) => api.patch(`/resources/deployments/${id}/approve`).then(r => r.data);
export const submitIncident = (payload) => api.post('/incidents/', payload).then(r => r.data);
export const fetchWeather = () => api.get('/weather/current').then(r => r.data);
export const fetchMlPredictions = () => api.get('/ml/predict/all').then(r => r.data);
export const fetchMlZone = (zoneId) => api.get(`/ml/predict/${zoneId}`).then(r => r.data);
