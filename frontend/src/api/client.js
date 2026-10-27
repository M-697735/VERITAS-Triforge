import axios from 'axios';

const API_BASE = '/api';

export const analyzeEmail = async (fileOrContent, isRawText = false, liveReverify = false) => {
  const formData = new FormData();
  if (isRawText) {
    formData.append('raw_content', fileOrContent);
  } else {
    formData.append('file', fileOrContent);
  }
  formData.append('live_reverify', liveReverify);

  const response = await axios.post(`${API_BASE}/analyze`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const fetchSamples = async () => {
  const response = await axios.get(`${API_BASE}/samples`);
  return response.data;
};

export const fetchSampleContent = async (sampleId) => {
  const response = await axios.get(`${API_BASE}/samples/${sampleId}`);
  return response.data;
};

export const checkHealth = async () => {
  const response = await axios.get(`${API_BASE}/health`, { timeout: 2500 });
  return response.data;
};

export const downloadPdfReport = async (analysisData) => {
  const payload = analysisData?.case_id ? { case_id: analysisData.case_id } : analysisData;
  const response = await axios.post(`${API_BASE}/report/pdf`, payload, {
    responseType: 'blob',
  });
  
  const blob = new Blob([response.data], { type: 'application/pdf' });
  const downloadUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = downloadUrl;
  const hashPrefix = (analysisData?.sha256_hash || 'report').substring(0, 8);
  const cid = analysisData?.case_id || 'case';
  link.setAttribute('download', `VERITAS_${cid}_${hashPrefix}.pdf`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(downloadUrl);
};

export const fetchHistory = async () => {
  const response = await axios.get(`${API_BASE}/history`);
  return response.data;
};

export const fetchCaseDetail = async (caseId) => {
  const response = await axios.get(`${API_BASE}/history/${caseId}`);
  return response.data;
};

export const saveCase = async (caseId, label = null) => {
  const payload = { case_id: caseId };
  if (label) payload.label = label;
  const response = await axios.post(`${API_BASE}/history/save`, payload);
  return response.data;
};

export const deleteCase = async (caseId) => {
  const response = await axios.delete(`${API_BASE}/history/${caseId}`);
  return response.data;
};

export const clearHistory = async () => {
  const response = await axios.delete(`${API_BASE}/history`);
  return response.data;
};

export const fetchInbox = async () => {
  const response = await axios.get(`${API_BASE}/inbox`);
  return response.data;
};

export const fetchInboxItem = async (inboxId) => {
  const response = await axios.get(`${API_BASE}/inbox/${inboxId}`);
  return response.data;
};

export const reviewInboxItem = async (inboxId) => {
  const response = await axios.post(`${API_BASE}/inbox/${inboxId}/review`);
  return response.data;
};

export const saveInboxItem = async (inboxId, label = null) => {
  const payload = label ? { label } : {};
  const response = await axios.post(`${API_BASE}/inbox/${inboxId}/save`, payload);
  return response.data;
};

export const deleteInboxItem = async (inboxId) => {
  const response = await axios.delete(`${API_BASE}/inbox/${inboxId}`);
  return response.data;
};

export const fetchIngestStatus = async () => {
  const response = await axios.get(`${API_BASE}/ingest/status`);
  return response.data;
};

export const fetchImapConfig = async () => {
  const response = await axios.get(`${API_BASE}/ingest/imap/config`);
  return response.data;
};

export const testImapConnection = async (config) => {
  const response = await axios.post(`${API_BASE}/ingest/imap/test`, config);
  return response.data;
};

export const configureImap = async (config) => {
  const response = await axios.post(`${API_BASE}/ingest/imap/configure`, config);
  return response.data;
};

export const disconnectImap = async () => {
  const response = await axios.post(`${API_BASE}/ingest/imap/disconnect`);
  return response.data;
};

export const syncImapNow = async () => {
  const response = await axios.post(`${API_BASE}/ingest/imap/sync`);
  return response.data;
};



