const API_BASE = process.env.REACT_APP_API_URL || '';

export const api = {
  getCurrentData: () => fetch(`${API_BASE}/api/current_data`).then(res => res.json()),
  getEventLog: () => fetch(`${API_BASE}/api/event_log`).then(res => res.json()),
  getSeatAssignments: () => fetch(`${API_BASE}/api/seat_assignments`).then(res => res.json()),
  getMetrics: () => fetch(`${API_BASE}/api/metrics`).then(res => res.json()),
  uploadFile: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch(`${API_BASE}/upload`, { method: 'POST', body: formData }).then(res => res.json());
  },
  processFile: (filePath, fileType) => 
    fetch(`${API_BASE}/process_file`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: filePath, file_type: fileType })
    }).then(res => res.json())
};