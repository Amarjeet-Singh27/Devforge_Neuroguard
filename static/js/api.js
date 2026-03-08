// ===== NeuroGuard API Helper =====

const API_BASE = (() => {
  const host = window.location.hostname;
  const port = window.location.port;
  const isLocalhost = host === 'localhost' || host === '127.0.0.1';

  // If UI is served by Flask on :5001, use same origin.
  if (port === '5001') {
    return `${window.location.origin}/api`;
  }

  // If UI is served by a local static/dev server, still target Flask backend on :5001.
  if (isLocalhost) {
    return `http://${host}:5001/api`;
  }

  // Default to same-origin for deployed environments behind a reverse proxy.
  return `${window.location.origin}/api`;
})();

class NeuroGuardAPI {
  constructor() {
    this.token = localStorage.getItem('access_token');
    this.currentUser = null;
    this.currentUserPromise = null;
  }

  // ===== Auth Methods =====
  async register(email, password, fullName, userType, age = null, verificationToken = null) {
    try {
      const response = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email, password, full_name: fullName, user_type: userType, age, verification_token: verificationToken
        })
      });
      const data = await response.json();
      if (response.ok) {
        this.setToken(data.access_token);
        return { success: true, data };
      }
      return { success: false, error: data.error };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async requestSignupOtp(email) {
    try {
      const response = await fetch(`${API_BASE}/auth/request-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      const data = await response.json();
      return { success: response.ok, data, error: data.error };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async verifySignupOtp(email, otp) {
    try {
      const response = await fetch(`${API_BASE}/auth/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, otp })
      });
      const data = await response.json();
      return { success: response.ok, data, error: data.error };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getOtpStatus() {
    try {
      const response = await fetch(`${API_BASE}/auth/otp-status`);
      const data = await response.json();
      return { success: response.ok, data, error: data.error };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async login(email, password) {
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await response.json();
      if (response.ok) {
        this.setToken(data.access_token);
        return { success: true, data };
      }
      return { success: false, error: data.error };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getProfile() {
    try {
      const response = await fetch(`${API_BASE}/auth/profile`, {
        headers: this.getAuthHeader()
      });
      const data = await response.json();
      return { success: response.ok, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getCurrentUser(forceRefresh = false) {
    if (!forceRefresh && this.currentUser) {
      return { success: true, data: this.currentUser };
    }
    if (!forceRefresh && this.currentUserPromise) {
      return this.currentUserPromise;
    }

    this.currentUserPromise = this.getProfile()
      .then((result) => {
        if (result.success && result.data) {
          this.currentUser = result.data;
        }
        return result;
      })
      .finally(() => {
        this.currentUserPromise = null;
      });

    return this.currentUserPromise;
  }

  isAdminUser(user) {
    return ((user && user.user_type) || '').toLowerCase() === 'admin';
  }

  setVisibility(el, show) {
    if (!el) return;
    if (show) {
      el.style.display = el.dataset.prevDisplay || '';
      return;
    }
    if (el.dataset.prevDisplay === undefined) {
      el.dataset.prevDisplay = el.style.display || '';
    }
    el.style.display = 'none';
  }

  async applyRoleBasedVisibility() {
    const adminOnlyTargets = Array.from(document.querySelectorAll('.admin-only'));
    if (!adminOnlyTargets.length) return;

    if (!this.isAuthenticated()) {
      adminOnlyTargets.forEach((el) => this.setVisibility(el, false));
      return;
    }

    const profile = await this.getCurrentUser();
    const isAdmin = profile.success && this.isAdminUser(profile.data);
    adminOnlyTargets.forEach((el) => this.setVisibility(el, isAdmin));

    const isAdminPage = window.location.pathname.includes('/admin-messages.html');
    if (isAdminPage && !isAdmin) {
      showAlert('Admin access required', 'warning');
      setTimeout(() => {
        window.location.href = '/dashboard.html';
      }, 250);
    }
  }

  async updateProfile(fullName, age, medicalHistory) {
    try {
      const response = await fetch(`${API_BASE}/auth/update-profile`, {
        method: 'PUT',
        headers: { ...this.getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: fullName, age, medical_history: medicalHistory
        })
      });
      const data = await response.json();
      return { success: response.ok, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // ===== Voice Methods =====
  async uploadVoiceTest(audioFile, metadata = {}) {
    try {
      const formData = new FormData();
      const extByType = {
        'audio/wav': 'wav',
        'audio/x-wav': 'wav',
        'audio/mpeg': 'mp3',
        'audio/mp3': 'mp3',
        'audio/ogg': 'ogg',
        'audio/webm': 'webm',
        'audio/mp4': 'm4a',
        'audio/x-m4a': 'm4a',
        'audio/flac': 'flac',
        'audio/x-flac': 'flac'
      };
      const fallbackExt = extByType[(audioFile.type || '').toLowerCase()] || 'wav';
      const uploadName = audioFile.name || `recording.${fallbackExt}`;
      formData.append('audio', audioFile, uploadName);
      if (metadata.reference_sentence) {
        formData.append('reference_sentence', metadata.reference_sentence);
      }
      if (metadata.source) {
        formData.append('source', metadata.source);
      }

      const response = await fetch(`${API_BASE}/voice/test`, {
        method: 'POST',
        headers: this.getAuthHeaderNoContentType(),
        body: formData
      });
      const contentType = response.headers.get('content-type') || '';
      let data = {};
      if (contentType.includes('application/json')) {
        data = await response.json();
      } else {
        const raw = await response.text();
        data = { error: `Server returned non-JSON response (${response.status}).` };
        console.error('[API][uploadVoiceTest] Non-JSON response:', raw.slice(0, 300));
      }
      if (response.ok) {
        return { success: true, data };
      }
      const errorMsg = data.error || data.msg || 'Voice analysis failed';
      if (typeof errorMsg === 'string' && (
        errorMsg.toLowerCase().includes('signature verification failed') ||
        errorMsg.toLowerCase().includes('token has expired') ||
        errorMsg.toLowerCase().includes('invalid token')
      )) {
        this.clearToken();
        setTimeout(() => {
          window.location.href = '/';
        }, 100);
      }
      return { success: false, error: errorMsg };
    } catch (error) {
      return { success: false, error: error.message || 'Network error occurred' };
    }
  }

  async getVoiceHistory() {
    try {
      const response = await fetch(`${API_BASE}/voice/history`, {
        headers: this.getAuthHeader()
      });
      const data = await response.json();
      return { success: response.ok, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getVoiceTest(testId) {
    try {
      const response = await fetch(`${API_BASE}/voice/test/${testId}`, {
        headers: this.getAuthHeader()
      });
      const data = await response.json();
      return { success: response.ok, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getVoiceStats() {
    try {
      const response = await fetch(`${API_BASE}/voice/stats`, {
        headers: this.getAuthHeader()
      });
      const data = await response.json();
      return { success: response.ok, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async downloadVoiceReport(testId) {
    try {
      const response = await fetch(`${API_BASE}/voice/test/${testId}/report.pdf`, {
        headers: this.getAuthHeaderNoContentType()
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        return { success: false, error: data.error || 'Failed to download report' };
      }

      const blob = await response.blob();
      const disposition = response.headers.get('Content-Disposition') || '';
      let filename = `voice_report_${testId}.pdf`;
      const match = disposition.match(/filename=\"?([^\";]+)\"?/i);
      if (match && match[1]) {
        filename = match[1];
      }

      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);

      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // ===== Medicine Methods =====
  async registerMedicineBatch(batchId, name, manufacturer, expiryDate) {
    try {
      const response = await fetch(`${API_BASE}/medicine/register-batch`, {
        method: 'POST',
        headers: { ...this.getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          batch_id: batchId, name, manufacturer, expiry_date: expiryDate
        })
      });
      const data = await response.json();
      return { success: response.ok, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async addSupplyChainRecord(batchId, location, handler) {
    try {
      const response = await fetch(`${API_BASE}/medicine/add-supply-chain`, {
        method: 'POST',
        headers: { ...this.getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_id: batchId, location, handler })
      });
      const data = await response.json();
      return { success: response.ok, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async verifyMedicine(batchId) {
    try {
      const response = await fetch(`${API_BASE}/medicine/verify/${batchId}`);
      const data = await response.json();
      return { success: response.ok, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async generateQR(batchId) {
    try {
      const response = await fetch(`${API_BASE}/medicine/qr-generate/${batchId}`);
      const data = await response.json();
      return { success: response.ok, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async listMedicineBatches(page = 1, perPage = 10) {
    try {
      const response = await fetch(`${API_BASE}/medicine/list-batches?page=${page}&per_page=${perPage}`, {
        headers: this.getAuthHeader()
      });
      const data = await response.json();
      return { success: response.ok, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // ===== Contact Methods =====
  async submitContactMessage(name, email, subject, message) {
    try {
      const response = await fetch(`${API_BASE}/contact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, subject, message })
      });
      const data = await response.json();
      return { success: response.ok, data, error: data.error };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getContactMessages() {
    try {
      const response = await fetch(`${API_BASE}/contact/list`, {
        headers: this.getAuthHeader()
      });
      const data = await response.json();
      return { success: response.ok, data, error: data.error };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // ===== Utility Methods =====
  setToken(token) {
    this.token = token;
    localStorage.setItem('access_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('access_token');
  }

  isAuthenticated() {
    return this.token !== null && this.token !== undefined;
  }

  getAuthHeader() {
    return {
      'Authorization': `Bearer ${this.token}`,
      'Content-Type': 'application/json'
    };
  }

  getAuthHeaderNoContentType() {
    return {
      'Authorization': `Bearer ${this.token}`
    };
  }

  logout() {
    this.clearToken();
    window.location.href = '/';
  }
}

// Create global instance
const api = new NeuroGuardAPI();

// Utility function to show toast notifications (enhanced)
function showAlert(message, type = 'info') {
  // Create toast container if it doesn't exist
  let toastContainer = document.getElementById('toastContainer');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toastContainer';
    toastContainer.className = 'toast-container';
    document.body.appendChild(toastContainer);
  }

  // Create toast element
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  const icons = {
    success: '✓',
    danger: '✕',
    warning: '⚠',
    info: 'ℹ'
  };

  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || '•'}</span>
    <span>${message}</span>
    <span class="toast-close">×</span>
  `;

  toastContainer.appendChild(toast);

  // Close button handler
  toast.querySelector('.toast-close').addEventListener('click', () => {
    toast.style.animation = 'fadeOut 0.3s ease-out';
    setTimeout(() => toast.remove(), 300);
  });

  // Auto remove after 5 seconds
  setTimeout(() => {
    if (toast.parentElement) {
      toast.style.animation = 'fadeOut 0.3s ease-out';
      setTimeout(() => toast.remove(), 300);
    }
  }, 5000);
}

// Show loading spinner
function showLoading(message = 'Loading...') {
  const loader = document.createElement('div');
  loader.id = 'loadingOverlay';
  loader.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    animation: fadeIn 0.3s ease;
  `;

  const content = document.createElement('div');
  content.style.cssText = `
    background: white;
    padding: 2rem;
    border-radius: 10px;
    text-align: center;
    animation: scaleIn 0.3s ease-out;
  `;

  content.innerHTML = `
    <div class="spinner" style="margin: 0 auto 1rem;"></div>
    <p style="color: #6b7280;">${message}</p>
  `;

  loader.appendChild(content);
  document.body.appendChild(loader);
  return loader;
}

// Hide loading spinner
function hideLoading() {
  const loader = document.getElementById('loadingOverlay');
  if (loader) {
    loader.style.animation = 'fadeOut 0.3s ease';
    setTimeout(() => loader.remove(), 300);
  }
}

// Page transition wrapper
function transitionPage(callback) {
  const mainContent = document.querySelector('body');
  mainContent.style.animation = 'fadeOut 0.3s ease';
  
  setTimeout(() => {
    callback();
    mainContent.style.animation = 'fadeIn 0.3s ease';
  }, 300);
}

// Utility function to format date
function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Check authentication on page load
document.addEventListener('DOMContentLoaded', () => {
  if (!window.location.pathname.includes('index.html') && window.location.pathname !== '/' && !api.isAuthenticated()) {
    // Redirect to login if not authenticated (except on login page)
    if (!window.location.pathname.includes('register.html')) {
      // window.location.href = '/';
    }
  }
  api.applyRoleBasedVisibility();
});
