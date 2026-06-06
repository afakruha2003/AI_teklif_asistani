import axios from 'axios';

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({ baseURL: `${BASE}/api/v1` });

// Products
export const getProducts = (params) => api.get('/products/', { params });
export const createProduct = (data) => api.post('/products/', data);
export const updateProduct = (id, data) => api.patch(`/products/${id}`, data);
export const deleteProduct = (id) => api.delete(`/products/${id}`);

// Knowledge
export const getKnowledge = (params) => api.get('/knowledge/', { params });
export const createKnowledge = (data) => api.post('/knowledge/', data);
export const updateKnowledge = (id, data) => api.patch(`/knowledge/${id}`, data);
export const deleteKnowledge = (id) => api.delete(`/knowledge/${id}`);

// Quotes
export const getQuotes = (params) => api.get('/quotes/', { params });
export const getQuote = (id) => api.get(`/quotes/${id}`);
export const createQuote = (params) => api.post('/quotes/', null, { params });

// Sessions
export const getSessions = (params) => api.get('/sessions/', { params });
export const getSessionMessages = (id) => api.get(`/sessions/${id}/messages`);
export const getSessionToolCalls = (id) => api.get(`/sessions/${id}/tool-calls`);

// SSE stream URL
export const streamUrl = () => `${BASE}/api/v1/chat/stream`;
