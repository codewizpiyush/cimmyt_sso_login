/**
 * Central SSO Admin Portal — Frontend Controller
 * Multi-Platform Identity Management (PostgreSQL sso_db)
 */

// Global State
let adminToken = localStorage.getItem('sso_admin_token') || null;
let currentAdmin = null;

let users = [];
let platforms = [];

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initAuth();
  initTabs();
  initModals();
  bindFormEvents();
});

// ========================================================
// 1. AUTHENTICATION & SESSION MANAGEMENT
// ========================================================

function initAuth() {
  const storedUser = localStorage.getItem('sso_admin_user');
  if (storedUser) {
    try {
      currentAdmin = JSON.parse(storedUser);
    } catch {
      currentAdmin = null;
    }
  }

  if (adminToken && currentAdmin) {
    showDashboardView();
    loadAllData();
  } else {
    showLoginView();
  }

  // Admin login form submit
  const loginForm = document.getElementById('admin-login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', handleAdminLogin);
  }

  // Logout button
  const logoutBtn = document.getElementById('btn-logout');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
  }
}

function showLoginView() {
  document.getElementById('login-screen')?.classList.remove('hidden');
  document.getElementById('admin-dashboard')?.classList.add('hidden');
  const errorMsg = document.getElementById('login-error-msg');
  if (errorMsg) {
    errorMsg.textContent = '';
    errorMsg.classList.add('hidden');
  }
}

function showDashboardView() {
  document.getElementById('login-screen')?.classList.add('hidden');
  document.getElementById('admin-dashboard')?.classList.remove('hidden');

  if (currentAdmin) {
    const nameEl = document.getElementById('admin-display-name');
    const avatarEl = document.getElementById('admin-avatar');
    if (nameEl) nameEl.textContent = currentAdmin.full_name || currentAdmin.username || 'Admin';
    if (avatarEl) {
      const initial = (currentAdmin.full_name || currentAdmin.username || 'A')[0].toUpperCase();
      avatarEl.textContent = initial;
    }
  }
}

async function handleAdminLogin(e) {
  e.preventDefault();
  const identifier = document.getElementById('admin-login-identifier')?.value.trim();
  const password = document.getElementById('admin-login-password')?.value;
  const submitBtn = document.getElementById('btn-admin-login-submit');
  const errorEl = document.getElementById('login-error-msg');

  if (!identifier || !password) return;

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span>Verifying Admin Access...</span>';
  }
  if (errorEl) {
    errorEl.classList.add('hidden');
    errorEl.textContent = '';
  }

  try {
    const res = await fetch('/api/sso/auth/admin-login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier, password }),
    });

    const data = await res.json();

    if (!res.ok) {
      const detail = data.detail || 'Sign in failed. Check your administrator credentials.';
      if (errorEl) {
        errorEl.textContent = detail;
        errorEl.classList.remove('hidden');
      }
      return;
    }

    // Success
    adminToken = data.token;
    currentAdmin = data.user;
    localStorage.setItem('sso_admin_token', adminToken);
    localStorage.setItem('sso_admin_user', JSON.stringify(currentAdmin));

    showToast(`Welcome, ${currentAdmin.full_name || currentAdmin.username}!`, 'success');
    showDashboardView();
    loadAllData();
  } catch (err) {
    console.error('Admin login error:', err);
    if (errorEl) {
      errorEl.textContent = 'Cannot reach SSO server. Check that the service is running.';
      errorEl.classList.remove('hidden');
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `
        <span>Sign In to Admin Console</span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"></path><path d="M12 5l7 7-7 7"></path></svg>
      `;
    }
  }
}

function handleLogout() {
  adminToken = null;
  currentAdmin = null;
  localStorage.removeItem('sso_admin_token');
  localStorage.removeItem('sso_admin_user');
  showToast('You have signed out of the SSO administration console.', 'success');
  showLoginView();
}

// Authenticated Fetch Wrapper
async function authFetch(url, options = {}) {
  const headers = options.headers ? { ...options.headers } : {};
  if (adminToken) {
    headers['Authorization'] = `Bearer ${adminToken}`;
  }
  headers['Content-Type'] = headers['Content-Type'] || 'application/json';

  const res = await fetch(url, { ...options, headers });
  if (res.status === 401 || res.status === 403) {
    const errorBody = await res.clone().json().catch(() => ({}));
    if (res.status === 401) {
      showToast('Admin session expired. Please sign in again.', 'error');
      handleLogout();
    }
    throw new Error(errorBody.detail || `Access denied (${res.status})`);
  }
  return res;
}

// Toast Notifications
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// ========================================================
// 2. DATA LOADING & SYNCHRONIZATION
// ========================================================

async function loadAllData() {
  try {
    await Promise.all([
      fetchPlatforms(),
      fetchUsers(),
    ]);

    renderAllViews();
    updateDashboardStats();
  } catch (err) {
    console.error('Failed to load SSO data:', err);
    showToast('Failed to load catalog data from PostgreSQL', 'error');
  }
}

async function fetchPlatforms() {
  const res = await authFetch('/api/sso/platforms');
  const data = await res.json();
  platforms = data.platforms || [];
  populatePlatformDropdowns();
}

async function fetchUsers() {
  const res = await authFetch('/api/sso/users');
  const data = await res.json();
  users = data.users || [];
}

function renderAllViews() {
  renderUsersTable();
  renderPlatformsGrid();
}

function updateDashboardStats() {
  const totalUsersEl = document.getElementById('stat-total-users');
  const totalAdminsEl = document.getElementById('stat-total-admins');
  const totalStandardEl = document.getElementById('stat-total-standard');
  const totalPlatformsEl = document.getElementById('stat-total-platforms');

  const admins = users.filter(u => u.global_role_id === 'admin').length;
  const standard = users.filter(u => u.global_role_id === 'standard').length;

  if (totalUsersEl) totalUsersEl.textContent = users.length;
  if (totalAdminsEl) totalAdminsEl.textContent = admins;
  if (totalStandardEl) totalStandardEl.textContent = standard;
  if (totalPlatformsEl) totalPlatformsEl.textContent = platforms.length;
}

// ========================================================
// 3. TABS & NAVIGATION
// ========================================================

function initTabs() {
  const tabs = document.querySelectorAll('.nav-item');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const targetPane = tab.dataset.tab;
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      const activePane = document.getElementById(`pane-${targetPane}`);
      if (activePane) activePane.classList.add('active');

      const title = document.getElementById('page-title');
      const subtitle = document.getElementById('page-subtitle');
      const headerActions = document.getElementById('header-actions');

      if (targetPane === 'users') {
        title.textContent = 'Users & Global Roles';
        subtitle.textContent = 'Central user directory. Users are allotted Administrator or Standard User.';
        if (headerActions) headerActions.style.display = 'block';
      } else if (targetPane === 'platforms') {
        title.textContent = 'Platforms & Domains';
        subtitle.textContent = 'Connected applications, allowed domains, and client API keys';
        if (headerActions) headerActions.style.display = 'none';
      } else if (targetPane === 'api-hub') {
        title.textContent = 'API Hub & Developer Center';
        subtitle.textContent = 'Complete SSO API documentation, live JSON schemas, and client website integration blueprint';
        if (headerActions) headerActions.style.display = 'none';
      } else {
        title.textContent = 'Platform Login Tester';
        subtitle.textContent = 'Simulate how e-Agrology or Agrotutor authenticates credentials and receives global role';
        if (headerActions) headerActions.style.display = 'none';
      }
    });
  });
}

// ========================================================
// 4. USERS MANAGEMENT TAB
// ========================================================

function renderUsersTable() {
  const tbody = document.getElementById('users-table-body');
  if (!tbody) return;

  const searchQuery = document.getElementById('user-search-input')?.value.toLowerCase().trim() || '';
  const globalRoleFilter = document.getElementById('user-global-role-filter')?.value || '';

  const filtered = users.filter(u => {
    const matchesSearch = !searchQuery ||
      (u.full_name && u.full_name.toLowerCase().includes(searchQuery)) ||
      (u.email && u.email.toLowerCase().includes(searchQuery)) ||
      (u.username && u.username.toLowerCase().includes(searchQuery));

    const matchesRole = !globalRoleFilter || u.global_role_id === globalRoleFilter;

    return matchesSearch && matchesRole;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">No users found matching your filters.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(u => {
    const initials = (u.full_name || u.email || 'U').substring(0, 2).toUpperCase();
    const roleBadge = u.global_role_id === 'admin'
      ? `<span class="badge badge-admin">ADMINISTRATOR</span>`
      : `<span class="badge badge-standard">STANDARD USER</span>`;

    const statusBadge = u.is_active
      ? `<span class="badge badge-success">ACTIVE</span>`
      : `<span class="badge badge-danger">DEACTIVATED</span>`;

    const createdDate = u.created_on ? new Date(u.created_on).toLocaleDateString() : '—';

    return `
      <tr>
        <td>
          <div class="user-cell">
            <div class="avatar">${initials}</div>
            <div class="user-info">
              <span class="user-name">${escapeHtml(u.full_name || '—')}</span>
              <span class="user-email">${escapeHtml(u.email)} ${u.username ? `(${escapeHtml(u.username)})` : ''}</span>
            </div>
          </div>
        </td>
        <td><code class="code-badge">${escapeHtml(u.user_id)}</code></td>
        <td>${roleBadge}</td>
        <td>${statusBadge}</td>
        <td class="text-dim" style="font-size: 12px;">${createdDate}</td>
        <td class="actions-col">
          <button class="btn btn-sm btn-outline" onclick="openEditUserModal('${u.user_id}')" title="Edit user">Edit</button>
          <button class="btn btn-sm btn-outline" onclick="openResetPasswordModal('${u.user_id}', '${escapeHtml(u.email)}')" title="Reset Password">Password</button>
          ${u.user_id !== currentAdmin?.user_id ? `<button class="btn btn-sm btn-danger-outline" onclick="handleDeleteUser('${u.user_id}')" title="Delete user">Delete</button>` : ''}
        </td>
      </tr>
    `;
  }).join('');
}

// Populate Platform Select Dropdowns
function populatePlatformDropdowns() {
  const testSelect = document.getElementById('test-platform-select');
  if (testSelect) {
    testSelect.innerHTML = platforms.map(p => `<option value="${p.app_id}">${escapeHtml(p.name)} (${p.app_id})</option>`).join('');
  }
}

// Open Edit User Modal
window.openEditUserModal = function(userId) {
  const user = users.find(u => u.user_id === userId);
  if (!user) return;

  document.getElementById('edit-user-id').value = user.user_id;
  document.getElementById('edit-user-name').value = user.full_name || '';
  document.getElementById('edit-user-email').value = user.email || '';
  document.getElementById('edit-user-username').value = user.username || '';
  document.getElementById('edit-user-global-role').value = user.global_role_id || 'standard';
  document.getElementById('edit-user-status').value = user.is_active ? '1' : '0';

  document.getElementById('modal-edit-user')?.classList.add('open');
};

// Open Reset Password Modal
window.openResetPasswordModal = function(userId, email) {
  document.getElementById('reset-pw-user-id').value = userId;
  const label = document.getElementById('reset-pw-user-label');
  if (label) label.textContent = `Set new credentials for user: ${email} (${userId})`;
  document.getElementById('reset-pw-input').value = '';
  document.getElementById('modal-reset-pw')?.classList.add('open');
};

// Delete User
window.handleDeleteUser = async function(userId) {
  if (!confirm(`Are you sure you want to permanently delete user ${userId}?`)) {
    return;
  }

  try {
    const res = await authFetch(`/api/sso/users/${userId}`, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to delete user');
    }
    showToast(`User ${userId} deleted successfully`, 'success');
    await fetchUsers();
    renderUsersTable();
    updateDashboardStats();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

// ========================================================
// 5. PLATFORMS & DOMAINS TAB
// ========================================================

function renderPlatformsGrid() {
  const container = document.getElementById('platforms-grid-container');
  if (!container) return;

  if (platforms.length === 0) {
    container.innerHTML = `<div class="loading-cell">No client platforms registered. Click "+ Add Platform" to connect a domain.</div>`;
    return;
  }

  container.innerHTML = platforms.map(p => {
    const domains = (p.allowed_domains || '').split(',').map(d => d.trim()).filter(Boolean);
    const domainItems = domains.map(d => `<div class="platform-domain-item">🌐 ${escapeHtml(d)}</div>`).join('');
    const isActive = p.is_active !== false;

    return `
      <div class="platform-card">
        <div class="platform-card-top">
          <span class="platform-card-name">${escapeHtml(p.name)}</span>
          <span class="platform-badge-slug">${escapeHtml(p.app_id)}</span>
        </div>
        <p class="platform-card-desc">${escapeHtml(p.description || 'Connected SSO Client Platform')}</p>

        <div class="platform-domains-box">
          <span class="platform-domains-label">Allowed Domains (${domains.length})</span>
          ${domainItems || '<span class="text-dim">No domains restricted</span>'}
        </div>

        <div class="platform-key-box">
          <div class="key-box-header">
            <span class="key-label">Client API Key (X-SSO-Api-Key)</span>
            <button class="btn-copy-sm" onclick="copyToClipboard('${escapeHtml(p.api_key)}', 'API Key')">Copy Key</button>
          </div>
          <div class="key-value-display">
            <code>${escapeHtml(p.api_key || '—')}</code>
          </div>
        </div>

        <div class="platform-card-meta">
          <span>Status: ${isActive ? '<strong style="color: #34D399;">Active</strong>' : '<strong style="color: #F87171;">Suspended</strong>'}</span>
          <span class="text-dim">Subroles & perms managed on platform</span>
        </div>

        <div class="platform-card-actions">
          <button class="btn btn-sm btn-outline" onclick="openEditPlatformModal('${escapeHtml(p.app_id)}')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
            <span>Edit Connection</span>
          </button>
          <button class="btn btn-sm btn-outline" onclick="viewPlatformApiDocs('${escapeHtml(p.app_id)}')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>
            <span>API Docs</span>
          </button>
          ${p.app_id !== 'eagrology' ? `
            <button class="btn btn-sm btn-danger-outline" onclick="handleDeletePlatform('${escapeHtml(p.app_id)}')">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
              <span>Delete</span>
            </button>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

// Open Edit Platform Modal
window.openEditPlatformModal = function(appId) {
  const p = platforms.find(x => x.app_id === appId);
  if (!p) return;

  document.getElementById('edit-platform-id').value = p.app_id;
  document.getElementById('edit-platform-id-display').value = p.app_id;
  document.getElementById('edit-platform-name').value = p.name || '';
  document.getElementById('edit-platform-domains').value = p.allowed_domains || '';
  document.getElementById('edit-platform-desc').value = p.description || '';
  document.getElementById('edit-platform-status').value = p.is_active !== false ? '1' : '0';

  document.getElementById('modal-edit-platform')?.classList.add('open');
};

// Delete Platform Connection
window.handleDeletePlatform = async function(appId) {
  if (!confirm(`Are you sure you want to unlink and delete platform connection '${appId}'? This will revoke its API key and SSO authentication permissions.`)) {
    return;
  }

  try {
    const res = await authFetch(`/api/sso/platforms/${appId}`, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to delete platform');
    }
    showToast(`Platform '${appId}' connection unlinked successfully`, 'success');
    await fetchPlatforms();
    renderPlatformsGrid();
    updateDashboardStats();
  } catch (err) {
    showToast(err.message, 'error');
  }
};

// Copy Text to Clipboard
window.copyToClipboard = function(text, label = 'Text') {
  if (!text) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      showToast(`${label} copied to clipboard!`, 'success');
    }).catch(() => {
      fallbackCopy(text, label);
    });
  } else {
    fallbackCopy(text, label);
  }
};

function fallbackCopy(text, label) {
  const ta = document.createElement('textarea');
  ta.value = text;
  document.body.appendChild(ta);
  ta.select();
  document.execCommand('copy');
  document.body.removeChild(ta);
  showToast(`${label} copied to clipboard!`, 'success');
}

// Copy cURL Command
window.copyCurl = function(elementId) {
  const el = document.getElementById(elementId);
  const text = el ? el.textContent : elementId;
  copyToClipboard(text, 'cURL command');
};

// Switch Tab to API Hub
window.viewPlatformApiDocs = function(appId) {
  const tabBtn = document.getElementById('tab-api-hub-btn');
  if (tabBtn) tabBtn.click();
};


// ========================================================
// 6. FORM SUBMISSIONS & MODALS
// ========================================================

function initModals() {
  document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', () => {
      const modalId = btn.dataset.close;
      document.getElementById(modalId)?.classList.remove('open');
    });
  });

  window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-backdrop')) {
      e.target.classList.remove('open');
    }
  });

  // Add User Trigger
  document.getElementById('btn-add-user')?.addEventListener('click', () => {
    document.getElementById('form-add-user')?.reset();
    document.getElementById('modal-add-user')?.classList.add('open');
  });

  // Add Platform Trigger
  document.getElementById('btn-add-platform')?.addEventListener('click', () => {
    document.getElementById('form-add-platform')?.reset();
    document.getElementById('modal-add-platform')?.classList.add('open');
  });
}

function bindFormEvents() {
  // Search & Filter Listeners
  document.getElementById('user-search-input')?.addEventListener('input', renderUsersTable);
  document.getElementById('user-global-role-filter')?.addEventListener('change', renderUsersTable);

  // Add User Form
  document.getElementById('form-add-user')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const payload = {
      full_name: document.getElementById('add-user-name')?.value.trim(),
      email: document.getElementById('add-user-email')?.value.trim(),
      username: document.getElementById('add-user-username')?.value.trim() || undefined,
      password: document.getElementById('add-user-password')?.value,
      global_role_id: document.getElementById('add-user-global-role')?.value || 'standard',
    };

    try {
      const res = await authFetch('/api/sso/users', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create user');
      }

      showToast(`User created as ${payload.global_role_id === 'admin' ? 'Administrator' : 'Standard User'}!`, 'success');
      document.getElementById('modal-add-user')?.classList.remove('open');
      await fetchUsers();
      renderUsersTable();
      updateDashboardStats();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // Edit User Form
  document.getElementById('form-edit-user')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const userId = document.getElementById('edit-user-id')?.value;
    if (!userId) return;

    const payload = {
      full_name: document.getElementById('edit-user-name')?.value.trim(),
      email: document.getElementById('edit-user-email')?.value.trim(),
      username: document.getElementById('edit-user-username')?.value.trim() || null,
      global_role_id: document.getElementById('edit-user-global-role')?.value,
      is_active: document.getElementById('edit-user-status')?.value === '1',
    };

    try {
      const res = await authFetch(`/api/sso/users/${userId}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to update user');
      }

      showToast(`User ${userId} updated successfully!`, 'success');
      document.getElementById('modal-edit-user')?.classList.remove('open');
      await fetchUsers();
      renderUsersTable();
      updateDashboardStats();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // Reset Password Form
  document.getElementById('form-reset-pw')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const userId = document.getElementById('reset-pw-user-id')?.value;
    const newPassword = document.getElementById('reset-pw-input')?.value;

    try {
      const res = await authFetch(`/api/sso/users/${userId}/reset-password`, {
        method: 'POST',
        body: JSON.stringify({ new_password: newPassword }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to reset password');
      }

      showToast(`Password updated for user ${userId}`, 'success');
      document.getElementById('modal-reset-pw')?.classList.remove('open');
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // Add Platform Form
  document.getElementById('form-add-platform')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      app_id: document.getElementById('add-platform-id')?.value.trim().toLowerCase(),
      name: document.getElementById('add-platform-name')?.value.trim(),
      allowed_domains: document.getElementById('add-platform-domains')?.value.trim(),
      description: document.getElementById('add-platform-desc')?.value.trim(),
    };

    try {
      const res = await authFetch('/api/sso/platforms', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to register platform');
      }

      const created = await res.json();
      showToast(`Platform '${created.name}' registered!`, 'success');
      document.getElementById('modal-add-platform')?.classList.remove('open');
      await fetchPlatforms();
      renderPlatformsGrid();
      updateDashboardStats();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // Edit Platform Form Submit
  document.getElementById('form-edit-platform')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const appId = document.getElementById('edit-platform-id')?.value;
    if (!appId) return;

    const payload = {
      name: document.getElementById('edit-platform-name')?.value.trim(),
      allowed_domains: document.getElementById('edit-platform-domains')?.value.trim(),
      description: document.getElementById('edit-platform-desc')?.value.trim(),
      is_active: document.getElementById('edit-platform-status')?.value === '1',
    };

    try {
      const res = await authFetch(`/api/sso/platforms/${appId}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to update platform connection');
      }

      showToast(`Platform '${appId}' updated successfully!`, 'success');
      document.getElementById('modal-edit-platform')?.classList.remove('open');
      await fetchPlatforms();
      renderPlatformsGrid();
      updateDashboardStats();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // API Hub Category Pill Filtering
  const catPills = document.querySelectorAll('.cat-pill');
  catPills.forEach(pill => {
    pill.addEventListener('click', () => {
      catPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');

      const selectedCat = pill.dataset.cat;
      const cards = document.querySelectorAll('.api-item-card');
      const guideBox = document.getElementById('api-integration-guide');

      if (selectedCat === 'guide') {
        guideBox?.scrollIntoView({ behavior: 'smooth' });
        return;
      }

      cards.forEach(card => {
        if (selectedCat === 'all' || card.dataset.cat === selectedCat) {
          card.style.display = 'block';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });

  // API Hub Search Filtering
  document.getElementById('api-search-input')?.addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase().trim();
    const cards = document.querySelectorAll('.api-item-card');
    cards.forEach(card => {
      const text = card.textContent.toLowerCase();
      const keywords = (card.dataset.keywords || '').toLowerCase();
      if (!q || text.includes(q) || keywords.includes(q)) {
        card.style.display = 'block';
      } else {
        card.style.display = 'none';
      }
    });
  });

  // Platform Authentication Simulator
  document.getElementById('btn-run-test-login')?.addEventListener('click', async () => {
    const appId = document.getElementById('test-platform-select')?.value || 'eagrology';
    const identifier = document.getElementById('test-login-id')?.value.trim();
    const password = document.getElementById('test-login-pw')?.value;
    const resultBox = document.getElementById('test-result-box');

    if (!identifier || !password) {
      showToast('Please enter username/email and password to test', 'error');
      return;
    }

    if (resultBox) {
      resultBox.classList.remove('hidden');
      resultBox.textContent = `Authenticating against target platform '${appId}'...`;
    }

    try {
      const res = await fetch('/api/sso/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier, password, app_id: appId }),
      });

      const data = await res.json();
      if (!res.ok) {
        resultBox.textContent = `HTTP ${res.status}: ${JSON.stringify(data, null, 2)}`;
        resultBox.style.borderColor = 'var(--danger)';
        return;
      }

      resultBox.style.borderColor = 'var(--success)';
      resultBox.textContent = `// Successful Authentication on Platform: "${appId}"\n` + JSON.stringify(data, null, 2);
    } catch (err) {
      if (resultBox) {
        resultBox.textContent = `Error: ${err.message}`;
        resultBox.style.borderColor = 'var(--danger)';
      }
    }
  });
}

// Utility: HTML Sanitizer
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
