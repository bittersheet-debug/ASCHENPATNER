/**
 * ASCHEN EVENT ORGANIZER - Admin Dashboard Frontend Script
 */

let currentAdmin = null;
let activeBookingId = null;
let ws = null;

// DOM Elements
const loginScreen = document.getElementById('loginScreen');
const appScreen = document.getElementById('appScreen');
const loginForm = document.getElementById('loginForm');
const loginAlert = document.getElementById('loginAlert');
const btnLogout = document.getElementById('btnLogout');
const btnRefresh = document.getElementById('btnRefresh');

const pageTitle = document.getElementById('pageTitle');
const pageDesc = document.getElementById('pageDesc');
const navItems = document.querySelectorAll('.nav-item');
const tabPanes = document.querySelectorAll('.tab-pane');

// Modal Elements
const bookingModal = document.getElementById('bookingModal');
const btnModalClose = document.getElementById('btnModalClose');
const modalBookingId = document.getElementById('modalBookingId');
const modalCategoryBadge = document.getElementById('modalCategoryBadge');
const modalFormRendered = document.getElementById('modalFormRendered');
const modalVenueSection = document.getElementById('modalVenueSection');
const modalVenueRendered = document.getElementById('modalVenueRendered');
const modalStatusSelect = document.getElementById('modalStatusSelect');
const modalEventDateInput = document.getElementById('modalEventDateInput');
const btnAcceptBooking = document.getElementById('btnAcceptBooking');
const btnRejectBooking = document.getElementById('btnRejectBooking');
const btnSendVenueForm = document.getElementById('btnSendVenueForm');
const btnUpdateStatus = document.getElementById('btnUpdateStatus');
const btnUpdateDate = document.getElementById('btnUpdateDate');
const btnCopyForm = document.getElementById('btnCopyForm');
const chatMessagesContainer = document.getElementById('chatMessagesContainer');
const chatForm = document.getElementById('chatForm');
const chatInputText = document.getElementById('chatInputText');
const modalStatusHistory = document.getElementById('modalStatusHistory');

// Toast
const toastNotification = document.getElementById('toastNotification');

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
  checkAuth();
  setupEventListeners();
});

function setupEventListeners() {
  // Login Form
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    loginAlert.classList.add('hidden');
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Login gagal.');

      currentAdmin = data.admin;
      showApp();
    } catch (err) {
      loginAlert.textContent = err.message;
      loginAlert.classList.remove('hidden');
    }
  });

  // Logout
  btnLogout.addEventListener('click', async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    currentAdmin = null;
    showLogin();
  });

  // Refresh
  btnRefresh.addEventListener('click', () => {
    loadDashboardData();
    showToast('Data berhasil diperbarui.');
  });

  // Navigation Tabs
  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const tab = item.getAttribute('data-tab');
      switchTab(tab);
    });
  });

  // Booking Filters
  const searchInput = document.getElementById('bookingSearchInput');
  const catSelect = document.getElementById('filterCategory');
  const statusSelect = document.getElementById('filterStatus');

  if (searchInput) searchInput.addEventListener('input', debounce(loadBookings, 300));
  if (catSelect) catSelect.addEventListener('change', loadBookings);
  if (statusSelect) statusSelect.addEventListener('change', loadBookings);

  // Modal Close
  btnModalClose.addEventListener('click', closeModal);
  bookingModal.addEventListener('click', (e) => {
    if (e.target === bookingModal) closeModal();
  });

  // Copy Form Text
  btnCopyForm.addEventListener('click', () => {
    navigator.clipboard.writeText(modalFormRendered.textContent);
    showToast('Format formulir disalin ke clipboard.');
  });

  // Modal Status Actions
  btnAcceptBooking.addEventListener('click', () => updateBookingStatusAction('Booking Diterima', 'Booking diterima oleh admin.'));
  btnRejectBooking.addEventListener('click', () => {
    const reason = prompt('Masukkan alasan penolakan booking:') || 'Pemesanan tidak dapat kami terima.';
    updateBookingStatusAction('Booking Ditolak', reason);
  });
  btnSendVenueForm.addEventListener('click', sendVenueReservationForm);

  btnUpdateStatus.addEventListener('click', () => {
    const status = modalStatusSelect.value;
    updateBookingStatusAction(status, `Status diubah secara manual menjadi ${status}`);
  });

  btnUpdateDate.addEventListener('click', () => {
    const newDate = modalEventDateInput.value.trim();
    if (!newDate) return alert('Masukkan tanggal acara.');
    updateBookingDate(newDate);
  });

  // Chat Form
  chatForm.addEventListener('submit', sendAdminChat);

  // Add Admin Form
  const addAdminForm = document.getElementById('addAdminForm');
  if (addAdminForm) {
    addAdminForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('newAdminName').value.trim();
      const username = document.getElementById('newAdminUsername').value.trim();
      const password = document.getElementById('newAdminPassword').value;
      const telegramId = document.getElementById('newAdminTelegramId').value.trim();

      try {
        const res = await fetch('/api/admins', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, username, password, telegramId: telegramId ? parseInt(telegramId, 10) : null })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        showToast('Admin baru berhasil ditambahkan.');
        addAdminForm.reset();
        loadAdmins();
      } catch (err) {
        alert(err.message);
      }
    });
  }

  // Add Channel Form
  const addChannelForm = document.getElementById('addChannelForm');
  if (addChannelForm) {
    addChannelForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const channelId = document.getElementById('manualChannelId').value.trim();
      const channelTitle = document.getElementById('manualChannelTitle').value.trim();

      try {
        const res = await fetch('/api/channels', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ channelId, channelTitle })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);

        showToast('Saluran notifikasi berhasil ditambahkan.');
        addChannelForm.reset();
        loadChannels();
      } catch (err) {
        alert(err.message);
      }
    });
  }

  // Test Channel Alert Button
  const btnTestChannelAlert = document.getElementById('btnTestChannelAlert');
  if (btnTestChannelAlert) {
    btnTestChannelAlert.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/channels/test', { method: 'POST' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);
        showToast('Pesan notifikasi uji coba berhasil dikirimkan ke channel!');
      } catch (err) {
        alert(`Gagal mengirim pesan uji coba: ${err.message}`);
      }
    });
  }

  // Webhook & Domain Listeners
  const btnConnectWebhook = document.getElementById('btnConnectWebhook');
  const btnDisconnectWebhook = document.getElementById('btnDisconnectWebhook');
  const btnCheckWebhook = document.getElementById('btnCheckWebhook');

  if (btnConnectWebhook) {
    btnConnectWebhook.addEventListener('click', connectWebhook);
  }
  if (btnDisconnectWebhook) {
    btnDisconnectWebhook.addEventListener('click', disconnectWebhook);
  }
  if (btnCheckWebhook) {
    btnCheckWebhook.addEventListener('click', loadWebhookStatus);
  }
}

// --- AUTH & VIEW SWITCHING ---
async function checkAuth() {
  try {
    const res = await fetch('/api/auth/me');
    if (res.ok) {
      const data = await res.json();
      currentAdmin = data.admin;
      showApp();
    } else {
      showLogin();
    }
  } catch (err) {
    showLogin();
  }
}

function showLogin() {
  loginScreen.classList.remove('hidden');
  appScreen.classList.add('hidden');
}

function showApp() {
  loginScreen.classList.add('hidden');
  appScreen.classList.remove('hidden');

  document.getElementById('loggedAdminName').textContent = currentAdmin.name || currentAdmin.username;
  document.getElementById('loggedAdminRole').textContent = currentAdmin.role === 'superadmin' ? 'Super Admin' : 'Admin Organizer';

  initWebSocket();
  loadDashboardData();
}

function switchTab(tabId) {
  navItems.forEach(item => {
    item.classList.toggle('active', item.getAttribute('data-tab') === tabId);
  });

  tabPanes.forEach(pane => {
    pane.classList.toggle('active', pane.id === `tab-${tabId}`);
  });

  const titles = {
    overview: ['Ringkasan Sistem', 'Sistem Pemesanan Event & Dashboard Operasional'],
    bookings: ['Daftar Pemesanan Event', 'Kelola seluruh formulir masuk, status, dan reservasi'],
    schedule: ['Jadwal Acara', 'Agenda acara yang telah diterima dan dikonfirmasi'],
    automated: ['Pesan Ucapan Terima Kasih Otomatis', 'Pengiriman otomatis pukul 19.00 WIB pada hari acara'],
    admins: ['Manajemen Admin', 'Daftar pengelola sistem dan hak akses']
  };

  if (titles[tabId]) {
    pageTitle.textContent = titles[tabId][0];
    pageDesc.textContent = titles[tabId][1];
  }

  if (tabId === 'overview') loadOverview();
  if (tabId === 'bookings') loadBookings();
  if (tabId === 'schedule') loadSchedule();
  if (tabId === 'automated') loadSchedulesTable();
  if (tabId === 'admins') {
    loadAdmins();
    loadChannels();
    loadWebhookStatus();
  }
}

// --- REAL-TIME LIVE SYNC & NOTIFICATION ENGINE ---
let liveSyncInterval = null;
let lastSeenBookingIds = new Set();
let isInitialLoad = true;

// Synthesize luxury notification chimes via Web Audio API (zero external assets needed)
function playChime(type = 'booking') {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    if (ctx.state === 'suspended') {
      ctx.resume();
    }

    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    if (type === 'chat') {
      // 2-tone melodic bubble pop for incoming customer chat
      osc.type = 'sine';
      osc.frequency.setValueAtTime(523.25, now); // C5
      osc.frequency.setValueAtTime(783.99, now + 0.08); // G5
      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.3);
    } else {
      // Luxury gold 3-tone arpeggio for new incoming booking
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(587.33, now); // D5
      osc.frequency.setValueAtTime(739.99, now + 0.12); // F#5
      osc.frequency.setValueAtTime(880.00, now + 0.24); // A5
      gain.gain.setValueAtTime(0.28, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.6);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.6);
    }
  } catch (e) {}
}

function startLiveSync() {
  if (liveSyncInterval) return;

  // Ultra-responsive 2.5s live sync cycle
  liveSyncInterval = setInterval(async () => {
    // 1. Sync stats & tables
    loadOverview(true);
    loadBookings(true);

    // 2. Sync active chat if modal is open
    if (activeBookingId && !bookingModal.classList.contains('hidden')) {
      pollActiveChat();
    }
  }, 2500);
}

async function pollActiveChat() {
  if (!activeBookingId || bookingModal.classList.contains('hidden')) return;
  try {
    const res = await fetch(`/api/bookings/${activeBookingId}/messages`);
    if (!res.ok) return;
    const data = await res.json();
    const currentBubbles = chatMessagesContainer.querySelectorAll('.chat-bubble');
    if (data.messages && data.messages.length > currentBubbles.length) {
      const lastMsg = data.messages[data.messages.length - 1];
      if (lastMsg.sender_type === 'customer') {
        playChime('chat');
        showToast(`💬 Pesan masuk dari ${lastMsg.sender_name}`);
      }
      renderChatMessages(data.messages);
    }
  } catch (e) {}
}

function initWebSocket() {
  startLiveSync(); // Guarantee live sync is ALWAYS running immediately

  if (ws) return;
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}`;

  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      document.getElementById('botStatusLabel').textContent = 'Sistem Realtime Aktif (WebSocket)';
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.event === 'new_booking') {
          playChime('booking');
          showToast(`🔔 Formulir baru masuk! ID: ${msg.data.booking_id} (${msg.data.category})`);
          loadDashboardData();
        } else if (msg.event === 'chat_message') {
          if (activeBookingId === msg.data.booking_id) {
            appendChatMessage(msg.data.message);
          } else {
            showToast(`💬 Pesan baru dari ${msg.data.message.sender_name} (${msg.data.booking_id})`);
          }
        } else if (msg.event === 'booking_status_updated') {
          if (activeBookingId === msg.data.booking_id) {
            loadBookingDetail(activeBookingId);
          }
          loadDashboardData();
        } else if (msg.event === 'venue_submitted') {
          showToast(`🏨 Reservasi tempat tercatat untuk ID: ${msg.data.booking_id}`);
          if (activeBookingId === msg.data.booking_id) {
            loadBookingDetail(activeBookingId);
          }
          loadDashboardData();
        }
      } catch (e) {}
    };

    ws.onerror = () => {
      document.getElementById('botStatusLabel').textContent = 'Sistem Realtime Aktif (Live Sync)';
    };

    ws.onclose = () => {
      document.getElementById('botStatusLabel').textContent = 'Sistem Realtime Aktif (Live Sync)';
      ws = null;
      setTimeout(initWebSocket, 20000);
    };
  } catch (err) {
    document.getElementById('botStatusLabel').textContent = 'Sistem Realtime Aktif (Live Sync)';
  }
}

// --- DATA LOADERS ---
async function loadDashboardData() {
  loadOverview();
  loadBookings();
  loadSchedulesTable();
}

async function loadOverview(isSilent = false) {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) return;
    const stats = await res.json();

    document.getElementById('statTotal').textContent = stats.totalBookings || 0;
    document.getElementById('statPending').textContent = stats.pending || 0;
    document.getElementById('statConfirmed').textContent = stats.confirmed || 0;
    document.getElementById('statCompleted').textContent = stats.completed || 0;

    const badgePending = document.getElementById('badgePending');
    if (stats.pending > 0) {
      badgePending.textContent = stats.pending;
      badgePending.classList.remove('hidden');
    } else {
      badgePending.classList.add('hidden');
    }

    // Recent Bookings Table
    const tbody = document.getElementById('overviewRecentTable');
    if (stats.recentBookings && stats.recentBookings.length > 0) {
      tbody.innerHTML = stats.recentBookings.map(b => `
        <tr>
          <td><strong>${b.booking_id}</strong></td>
          <td>${b.full_name || '-'}<br><small class="text-sub">@${b.username || 'user'}</small></td>
          <td>${b.category_name}</td>
          <td>${b.event_date}</td>
          <td>${getStatusBadge(b.status)}</td>
          <td>
            <button class="btn btn-xs btn-outline" onclick="openBookingModal('${b.booking_id}')">
              <i class="fa-solid fa-eye"></i> Detail
            </button>
          </td>
        </tr>
      `).join('');
    } else {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-sub">Belum ada formulir masuk.</td></tr>`;
    }

    // Category Distribution
    const distContainer = document.getElementById('categoryDistribution');
    if (stats.categoryStats && stats.categoryStats.length > 0) {
      distContainer.innerHTML = stats.categoryStats.map(c => `
        <div class="dist-item">
          <span class="name">${c.category_name}</span>
          <span class="count">${c.count} Pemesanan</span>
        </div>
      `).join('');
    } else {
      distContainer.innerHTML = `<p class="text-center text-sub py-3">Belum ada data kategori.</p>`;
    }

  } catch (err) {
    if (!isSilent) console.error('Error loading stats:', err);
  }
}

async function loadBookings(isSilent = false) {
  try {
    const search = document.getElementById('bookingSearchInput')?.value || '';
    const category = document.getElementById('filterCategory')?.value || '';
    const status = document.getElementById('filterStatus')?.value || '';

    const params = new URLSearchParams({ search, category, status });
    const res = await fetch(`/api/bookings?${params.toString()}`);
    if (!res.ok) return;
    const data = await res.json();

    const bookings = data.bookings || [];

    // Detect brand new incoming bookings
    const newItems = [];
    bookings.forEach(b => {
      if (!lastSeenBookingIds.has(b.booking_id)) {
        if (!isInitialLoad) {
          newItems.push(b);
        }
        lastSeenBookingIds.add(b.booking_id);
      }
    });

    if (!isInitialLoad && newItems.length > 0) {
      playChime('booking');
      const newest = newItems[0];
      showToast(`🔔 ${newItems.length} FORMULIR BARU MASUK DARI BOT! [${newest.booking_id}] ${newest.category_name} (${newest.full_name || '@' + newest.username})`);
      document.title = `(${newItems.length}) 🔔 FORMULIR BARU! — ASCHEN`;
      setTimeout(() => { document.title = 'ASCHEN EVENT ORGANIZER — Dashboard Admin'; }, 8000);
    }

    if (isInitialLoad && bookings.length > 0) {
      isInitialLoad = false;
    }

    const tbody = document.getElementById('bookingsTableBody');
    if (bookings.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-sub">Tidak ada pemesanan yang cocok dengan kriteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = bookings.map(b => {
      const isNew = newItems.some(item => item.booking_id === b.booking_id);
      const timeSubmitted = new Date(b.created_at).toLocaleString('id-ID', {
        day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
      });

      return `
        <tr class="${isNew ? 'row-new' : ''}">
          <td><strong class="text-gold">${b.booking_id}</strong></td>
          <td>
            <div>${b.full_name || '-'}</div>
            <small class="text-sub">@${b.username || 'user'}</small>
          </td>
          <td>${b.category_name}</td>
          <td>${b.event_date}</td>
          <td>${b.event_time}</td>
          <td>${getStatusBadge(b.status)}</td>
          <td><small class="text-sub">${timeSubmitted}</small></td>
          <td>
            <button class="btn btn-xs btn-gold" onclick="openBookingModal('${b.booking_id}')">
              <i class="fa-solid fa-folder-open"></i> Kelola
            </button>
          </td>
        </tr>
      `;
    }).join('');

  } catch (err) {
    if (!isSilent) console.error('Error loading bookings:', err);
  }
}

async function loadSchedule() {
  try {
    const res = await fetch('/api/bookings');
    if (!res.ok) return;
    const data = await res.json();

    // Filter confirmed/accepted bookings
    const confirmedList = data.bookings.filter(b => 
      ['Booking Diterima', 'Booking Dikonfirmasi', 'Reservasi Tempat Tercatat', 'Menunggu Reservasi Tempat'].includes(b.status)
    );

    const container = document.getElementById('scheduleTimeline');
    if (!confirmedList || confirmedList.length === 0) {
      container.innerHTML = `<p class="text-center text-sub py-4">Belum ada acara yang dikonfirmasi dalam agenda.</p>`;
      return;
    }

    container.innerHTML = confirmedList.map(b => `
      <div class="panel p-3 mb-2" style="border-left: 4px solid var(--gold-primary); margin-bottom: 1rem;">
        <div class="flex-between">
          <div>
            <h4 style="color: #fff; font-size: 1.05rem;">${b.category_name} — ${b.full_name || b.booking_id}</h4>
            <p class="text-sub" style="font-size: 0.85rem; margin-top: 0.2rem;">
              <i class="fa-solid fa-calendar"></i> ${b.event_date} &bull; <i class="fa-solid fa-clock"></i> ${b.event_time}
            </p>
          </div>
          <div>
            ${getStatusBadge(b.status)}
            <button class="btn btn-xs btn-outline ml-2" onclick="openBookingModal('${b.booking_id}')">Detail</button>
          </div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading schedule:', err);
  }
}

async function loadSchedulesTable() {
  try {
    const res = await fetch('/api/schedules');
    if (!res.ok) return;
    const data = await res.json();

    const tbody = document.getElementById('schedulesTableBody');
    if (!data.schedules || data.schedules.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-sub">Belum ada jadwal ucapan terima kasih otomatis. Jadwal dibuat ketika booking diterima atau dikonfirmasi.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.schedules.map(s => {
      const scheduledWIB = new Date(s.scheduled_at).toLocaleString('id-ID', {
        timeZone: 'Asia/Jakarta',
        day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
      }) + ' WIB';

      const sentTime = s.sent_at ? new Date(s.sent_at).toLocaleString('id-ID', {
        timeZone: 'Asia/Jakarta',
        day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
      }) + ' WIB' : '-';

      const statusBadge = s.status === 'sent' ? '<span class="badge badge-status diterima">Terkirim</span>' :
                          s.status === 'failed' ? `<span class="badge badge-status ditolak" title="${s.error_log || ''}">Gagal</span>` :
                          s.status === 'cancelled' ? '<span class="badge badge-status dibatalkan">Dibatalkan</span>' :
                          '<span class="badge badge-status terkirim">Menunggu Jadwal (19.00 WIB)</span>';

      return `
        <tr>
          <td><strong>${s.booking_id}</strong></td>
          <td>${s.full_name || '-'}<br><small class="text-sub">ID: ${s.telegram_id}</small></td>
          <td>${s.event_date}</td>
          <td>${scheduledWIB}</td>
          <td>${statusBadge}</td>
          <td>${sentTime}</td>
          <td>
            <button class="btn btn-xs btn-gold" onclick="triggerScheduleNow(${s.id})" ${s.status === 'sent' ? 'disabled' : ''}>
              <i class="fa-solid fa-paper-plane"></i> Uji Kirim Sekarang
            </button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading schedules:', err);
  }
}

async function triggerScheduleNow(scheduleId) {
  if (!confirm('Kirim pesan ucapan terima kasih otomatis sekarang ke pemesan?')) return;
  try {
    const res = await fetch(`/api/schedules/${scheduleId}/trigger`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    showToast('Pesan ucapan terima kasih berhasil dikirimkan!');
    loadSchedulesTable();
  } catch (err) {
    alert(`Gagal mengirim: ${err.message}`);
  }
}

async function loadAdmins() {
  try {
    const res = await fetch('/api/admins');
    if (!res.ok) return;
    const data = await res.json();

    const tbody = document.getElementById('adminsTableBody');
    tbody.innerHTML = data.admins.map(a => `
      <tr>
        <td><strong>${a.username}</strong></td>
        <td>${a.name}</td>
        <td>${a.telegram_id || '-'}</td>
        <td><span class="badge badge-status ${a.role === 'superadmin' ? 'dikonfirmasi' : 'reservasi_tercatat'}">${a.role}</span></td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Error loading admins:', err);
  }
}

async function loadChannels() {
  try {
    const res = await fetch('/api/channels');
    if (!res.ok) return;
    const data = await res.json();

    const tbody = document.getElementById('channelsTableBody');
    if (!data.channels || data.channels.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-center py-3 text-sub">Belum ada channel terhubung. Undang bot @ASCHENBOOKBOT ke channel Anda sebagai Administrator.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.channels.map(c => {
      const addedTime = new Date(c.added_at).toLocaleString('id-ID', {
        day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
      });

      return `
        <tr>
          <td><strong>${c.channel_title || 'Channel Telegram'}</strong></td>
          <td><code>${c.channel_username ? '@' + c.channel_username : c.channel_id}</code></td>
          <td><small class="text-sub">${addedTime}</small></td>
          <td>
            <button class="btn btn-xs btn-danger" onclick="deleteChannel('${c.channel_id}')">
              <i class="fa-solid fa-trash"></i> Hapus
            </button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading channels:', err);
  }
}

async function deleteChannel(channelId) {
  if (!confirm('Hapus saluran ini dari daftar penerima notifikasi booking?')) return;
  try {
    const res = await fetch(`/api/channels/${encodeURIComponent(channelId)}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    showToast('Saluran berhasil dihapus.');
    loadChannels();
  } catch (err) {
    alert(err.message);
  }
}

// --- DOMAIN & WEBHOOK TELEGRAM INTEGRATION ---
async function loadWebhookStatus() {
  const domainLabel = document.getElementById('currentDomainLabel');
  const badge = document.getElementById('webhookStatusBadge');
  const details = document.getElementById('webhookDetailsBox');

  if (domainLabel) {
    domainLabel.textContent = window.location.origin;
  }

  try {
    const res = await fetch('/api/webhook-info');
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    const info = data.info || {};
    if (info.url && info.url.length > 0) {
      if (badge) {
        badge.textContent = 'Webhook Aktif';
        badge.className = 'badge badge-status dikonfirmasi';
      }
      if (details) {
        details.innerHTML = `
          <strong>🔗 Webhook Terdaftar:</strong> ${escapeHtml(info.url)}<br>
          <strong>⏳ Antrean Pending:</strong> ${info.pending_update_count || 0} pembaruan<br>
          ${info.last_error_message ? `<strong style="color: #ff6b6b;">⚠️ Error Terakhir:</strong> ${escapeHtml(info.last_error_message)}<br>` : ''}
          ${info.last_error_date ? `<strong>🕒 Waktu Error:</strong> ${new Date(info.last_error_date * 1000).toLocaleString('id-ID')}<br>` : ''}
          <div style="margin-top: 6px; color: #a3e635;">✓ Siap menerima respon form dan pesan telegram langsung di domain ini!</div>
        `;
      }
    } else {
      if (badge) {
        badge.textContent = 'Mode Polling (Belum ada Webhook)';
        badge.className = 'badge badge-status menunggu_balasan';
      }
      if (details) {
        details.innerHTML = `Bot sedang berjalan dalam mode <strong>Long-Polling</strong> (lokal/VPS) atau belum memiliki Webhook. Jika website ini sudah memiliki Custom Domain di Vercel, klik tombol emas di bawah untuk menghubungkan Telegram ke domain Anda.`;
      }
    }
  } catch (err) {
    if (badge) {
      badge.textContent = 'Gagal Memeriksa';
      badge.className = 'badge badge-status ditolak';
    }
    if (details) {
      details.textContent = `Status: ${err.message}`;
    }
  }
}

async function connectWebhook() {
  const currentOrigin = window.location.origin;
  if (!confirm(`Sambungkan webhook Telegram ke domain saat ini?\nURL: ${currentOrigin}/api/webhook`)) return;

  try {
    const res = await fetch('/api/setup-webhook');
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    showToast('✅ Webhook Telegram berhasil disambungkan ke domain Anda!');
    loadWebhookStatus();
  } catch (err) {
    alert(`Gagal menyambungkan webhook: ${err.message}`);
  }
}

async function disconnectWebhook() {
  if (!confirm('Hapus webhook Telegram? Bot akan berhenti menerima update via webhook dan dapat kembali dijalankan secara polling di lokal atau VPS.')) return;

  try {
    const res = await fetch('/api/delete-webhook');
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    showToast('Webhook berhasil dihapus.');
    loadWebhookStatus();
  } catch (err) {
    alert(`Gagal menghapus webhook: ${err.message}`);
  }
}

// --- BOOKING MODAL ACTIONS ---
async function openBookingModal(bookingId) {
  activeBookingId = bookingId;
  await loadBookingDetail(bookingId);
  bookingModal.classList.remove('hidden');
}

function closeModal() {
  bookingModal.classList.add('hidden');
  activeBookingId = null;
}

async function loadBookingDetail(bookingId) {
  try {
    const res = await fetch(`/api/bookings/${bookingId}`);
    if (!res.ok) throw new Error('Gagal memuat detail booking.');
    const data = await res.json();

    const { booking, history, messages, statuses } = data;

    modalBookingId.textContent = booking.booking_id;
    modalCategoryBadge.textContent = booking.category_name;
    modalFormRendered.textContent = booking.rendered_preview;

    // Venue section
    if (booking.venue_rendered) {
      modalVenueRendered.textContent = booking.venue_rendered;
      modalVenueSection.classList.remove('hidden');
    } else {
      modalVenueSection.classList.add('hidden');
    }

    // Status Select
    modalStatusSelect.innerHTML = statuses.map(s => `
      <option value="${s}" ${s === booking.status ? 'selected' : ''}>${s}</option>
    `).join('');

    modalEventDateInput.value = booking.event_date;

    // Chat messages
    renderChatMessages(messages || []);

    // Status History
    renderStatusHistory(history || []);

  } catch (err) {
    alert(err.message);
  }
}

function renderChatMessages(messages) {
  if (messages.length === 0) {
    chatMessagesContainer.innerHTML = `<div class="text-center py-4 text-sub" style="font-size: 0.8rem;">Belum ada riwayat percakapan. Kirim pesan di bawah untuk memulai chat dengan pemesan.</div>`;
    return;
  }

  chatMessagesContainer.innerHTML = messages.map(m => {
    const time = new Date(m.created_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
    return `
      <div class="chat-bubble ${m.sender_type}">
        <div>${escapeHtml(m.message)}</div>
        <div class="chat-meta">
          <span>${m.sender_name}</span>
          <span>${time}</span>
        </div>
      </div>
    `;
  }).join('');

  chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
}

function appendChatMessage(message) {
  const time = new Date(message.created_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
  const html = `
    <div class="chat-bubble ${message.sender_type}">
      <div>${escapeHtml(message.message)}</div>
      <div class="chat-meta">
        <span>${message.sender_name}</span>
        <span>${time}</span>
      </div>
    </div>
  `;
  chatMessagesContainer.insertAdjacentHTML('beforeend', html);
  chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
}

async function sendAdminChat(e) {
  e.preventDefault();
  const text = chatInputText.value.trim();
  if (!text || !activeBookingId) return;

  try {
    const res = await fetch(`/api/bookings/${activeBookingId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    chatInputText.value = '';
    appendChatMessage(data.message);
  } catch (err) {
    alert(`Gagal mengirim pesan: ${err.message}`);
  }
}

function renderStatusHistory(history) {
  modalStatusHistory.innerHTML = history.map(h => {
    const time = new Date(h.created_at).toLocaleString('id-ID', {
      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
    });
    return `
      <div class="timeline-item">
        <div class="timeline-dot"></div>
        <div class="timeline-content">
          <strong>${h.new_status}</strong> &bull; <small style="display:inline;">${h.changed_by}</small>
          ${h.notes ? `<div style="color: var(--text-muted);">${h.notes}</div>` : ''}
          <small>${time}</small>
        </div>
      </div>
    `;
  }).join('');
}

async function updateBookingStatusAction(newStatus, notes = '') {
  if (!activeBookingId) return;
  try {
    const res = await fetch(`/api/bookings/${activeBookingId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus, notes })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    showToast(`Status berhasil diperbarui: ${newStatus}`);
    await loadBookingDetail(activeBookingId);
    loadDashboardData();
  } catch (err) {
    alert(`Gagal update status: ${err.message}`);
  }
}

async function sendVenueReservationForm() {
  if (!activeBookingId) return;
  if (!confirm('Kirimkan link ruang reservasi pertemuan (https://t.me/+NHhPUT9PqVw5YzIx) ke Telegram pemesan?')) return;

  try {
    const res = await fetch(`/api/bookings/${activeBookingId}/send-venue-form`, {
      method: 'POST'
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    showToast('Tautan ruang pertemuan berhasil dikirim ke bot pemesan!');
    await loadBookingDetail(activeBookingId);
    loadDashboardData();
  } catch (err) {
    alert(`Gagal mengirim tautan reservasi: ${err.message}`);
  }
}

async function updateBookingDate(newDate) {
  if (!activeBookingId) return;
  try {
    const res = await fetch(`/api/bookings/${activeBookingId}/update-date`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ eventDate: newDate })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    showToast('Tanggal acara dan jadwal pesan otomatis berhasil diperbarui.');
    await loadBookingDetail(activeBookingId);
    loadDashboardData();
  } catch (err) {
    alert(`Gagal update tanggal: ${err.message}`);
  }
}

// --- UTILITIES ---
function getStatusBadge(status) {
  const map = {
    'Formulir Terkirim': 'terkirim',
    'Menunggu Balasan Admin': 'menunggu_balasan',
    'Booking Diterima': 'diterima',
    'Booking Ditolak': 'ditolak',
    'Menunggu Reservasi Tempat': 'menunggu_reservasi',
    'Reservasi Tempat Tercatat': 'reservasi_tercatat',
    'Booking Dikonfirmasi': 'dikonfirmasi',
    'Booking Selesai': 'selesai',
    'Booking Dibatalkan': 'dibatalkan'
  };
  const cls = map[status] || 'terkirim';
  return `<span class="badge badge-status ${cls}">${status}</span>`;
}

function showToast(message) {
  toastNotification.textContent = message;
  toastNotification.classList.remove('hidden');
  setTimeout(() => {
    toastNotification.classList.add('hidden');
  }, 4000);
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function escapeHtml(str) {
  return str.replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}
