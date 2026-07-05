import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

export const authRegister = async (email: string, password: string) => {
  const response = await apiClient.post('/v1/auth/register', { email, password });
  return response.data;
};

export const authLogin = async (email: string, password: string) => {
  const response = await apiClient.post('/v1/auth/login', { email, password });
  return response.data;
};

export const authGoogle = async (token: string) => {
  const response = await apiClient.post('/v1/auth/google', { token });
  return response.data;
};

export const uploadFreeVideo = async (file: File, token: string, targetVmaf: number = 93.0, codec: string = "vp9", resolution: string = "original", audioBitrate: string = "96k") => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('target_vmaf', targetVmaf.toString());
  formData.append('codec', codec);
  formData.append('resolution', resolution);
  formData.append('audio_bitrate', audioBitrate);

  const response = await apiClient.post('/v1/optimize/free', formData, {
    headers: { 
      'Content-Type': 'multipart/form-data',
      'Authorization': `Bearer ${token}`
    },
  });
  return response.data;
};

export const getJobStatus = async (jobId: string, token: string) => {
  const response = await apiClient.get(`/v1/status/${jobId}`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  return response.data;
};

export const getUserDetails = async (token: string) => {
  const response = await apiClient.get('/v1/users/me', {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  return response.data;
};

export const getUserJobs = async (token: string) => {
  const response = await apiClient.get('/v1/jobs', {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  return response.data;
};
