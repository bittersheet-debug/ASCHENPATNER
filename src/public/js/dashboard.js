/**
 * ASCHEN EVENT ORGANIZER — Media Partner Client Application
 * Handles real-time telemetry, admin session, diagnostics, and table rendering.
 */

let isAdminLoggedIn = false;
let adminSessionToken = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  fetchSystemStatus();
  setInterval(fetchSystemStatus, 30000); // 30s auto-refresh
  setInterval(updateLiveClock, 1000);

  // Check saved admin session
  const savedToken = localStorage.getItem("aschen_admin_session");
  if (savedToken) {
    isAdminLoggedIn = true;
    adminSessionToken = savedToken;
  }
});

// Update WIB clock
function updateLiveClock() {
  const now = new Date();
  // Format WIB (UTC+7)
  const utc = now.getTime() + now.getTimezoneOffset() * 60000;
  const wibDate = new Date(utc + 7 * 3600000);
  const timeStr = wibDate.toLocaleTimeString("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  const clockEl = document.getElementById("wibClock");
  if (clockEl) {
    clockEl.textContent = `WIB: ${timeStr}`;
  }
}

// Fetch public metrics and status
async function fetchSystemStatus() {
  try {
    const res = await fetch("/api/mediapatner-api?action=status");
    if (!res.ok) return;
    const data = await res.json();

    if (data.success) {
      // Metrics
      const statReceived = document.getElementById("statReceived");
      const statKeep = document.getElementById("statKeep");
      const statPublished = document.getElementById("statPublished");
      const statNextSlot = document.getElementById("statNextSlot");
      const navStatusText = document.getElementById("navStatusText");
      const currentReportChatId = document.getElementById("currentReportChatId");

      if (statReceived) statReceived.textContent = data.stats.total_received || 0;
      if (statKeep) statKeep.textContent = data.stats.total_keep || 0;
      if (statPublished) statPublished.textContent = data.stats.total_published || 0;
      if (statNextSlot) statNextSlot.textContent = data.next_slot.display || "-";
      if (navStatusText) navStatusText.textContent = `${data.bot_username} Online`;
      if (currentReportChatId) currentReportChatId.textContent = data.report_chat_id || "-1004479248551";

      // Operational badge
      const opBadge = document.getElementById("opStatusBadge");
      if (opBadge) {
        if (data.operational.is_open) {
          opBadge.innerHTML = '<span class="badge badge-success">BUKA (ONLINE)</span>';
        } else {
          opBadge.innerHTML = '<span class="badge" style="background:rgba(239,68,68,0.2);color:#ef4444;">TUTUP</span>';
        }
      }
    }
  } catch (err) {
    console.warn("Could not fetch telemetry:", err);
  }
}

// Modal controls
function openAdminModal() {
  const modal = document.getElementById("adminModal");
  if (!modal) return;
  modal.classList.remove("hidden");

  if (isAdminLoggedIn) {
    showDashboardView();
  } else {
    showLoginView();
  }
}

function closeAdminModal() {
  const modal = document.getElementById("adminModal");
  if (modal) modal.classList.add("hidden");
}

function showLoginView() {
  document.getElementById("adminLoginForm").classList.remove("hidden");
  document.getElementById("adminDashboardContent").classList.add("hidden");
}

function showDashboardView() {
  document.getElementById("adminLoginForm").classList.add("hidden");
  document.getElementById("adminDashboardContent").classList.remove("hidden");
  fetchPosters();
}

// Admin Login
async function handleAdminLogin(e) {
  e.preventDefault();
  const passwordInput = document.getElementById("adminPasswordInput");
  const errorBox = document.getElementById("loginError");
  const password = passwordInput.value.trim();

  try {
    const res = await fetch("/api/mediapatner-api", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "login", password }),
    });
    const data = await res.json();

    if (data.success) {
      isAdminLoggedIn = true;
      adminSessionToken = data.token;
      localStorage.setItem("aschen_admin_session", data.token);
      errorBox.classList.add("hidden");
      showDashboardView();
    } else {
      errorBox.textContent = data.error || "Password salah.";
      errorBox.classList.remove("hidden");
    }
  } catch (err) {
    errorBox.textContent = "Gagal menghubungi server.";
    errorBox.classList.remove("hidden");
  }
}

function handleAdminLogout() {
  isAdminLoggedIn = false;
  adminSessionToken = null;
  localStorage.removeItem("aschen_admin_session");
  showLoginView();
}

// Tab Switching
function switchAdminTab(tabId) {
  document.querySelectorAll(".admin-nav-tabs .tab-btn").forEach((btn) => btn.classList.remove("active"));
  document.querySelectorAll(".tab-pane").forEach((pane) => pane.classList.remove("active"));

  const targetPane = document.getElementById(tabId);
  if (targetPane) targetPane.classList.add("active");

  const clickedBtn = event.currentTarget;
  if (clickedBtn) clickedBtn.classList.add("active");

  if (tabId === "tabPosters") fetchPosters();
  if (tabId === "tabReports") fetchReports();
  if (tabId === "tabDevices") fetchDevices();
}

// Fetch Posters
async function fetchPosters() {
  const tbody = document.getElementById("postersTableBody");
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" class="text-center">Memuat antrean...</td></tr>';

  try {
    const res = await fetch("/api/mediapatner-api?action=posters&limit=50");
    const data = await res.json();

    if (data.success && data.posters.length > 0) {
      tbody.innerHTML = data.posters.map((p) => `
        <tr>
          <td>#${p.id}</td>
          <td><strong>${p.sender_name}</strong><br><small class="text-muted">@${p.sender_username || "no_username"}</small></td>
          <td><span class="time-tag">${p.media_type || "forward"}</span></td>
          <td>${p.slot_day}, ${p.slot_time} WIB</td>
          <td><span class="badge ${p.status === 'PUBLISHED' ? 'badge-success' : 'badge-gold'}">${p.status}</span></td>
          <td>
            <div style="display:flex;gap:4px;flex-wrap:wrap;">
              ${(p.status === 'KEEP' || p.status === 'SCHEDULED') ? `<button class="btn btn-sm btn-gold" onclick="sebarPosterDuluan(${p.id})"><i class="fa-solid fa-rocket"></i> Sebar Duluan</button>` : ''}
              ${p.source_link ? `<a href="${p.source_link}" target="_blank" class="btn btn-sm btn-dark"><i class="fa-solid fa-arrow-up-right-from-square"></i> Cek</a>` : '-'}
            </div>
          </td>
        </tr>
      `).join("");
    } else {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Belum ada pengajuan poster.</td></tr>';
    }
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Gagal memuat data antrean.</td></tr>';
  }
}

// Fetch Reports
async function fetchReports() {
  const tbody = document.getElementById("reportsTableBody");
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" class="text-center">Memuat laporan...</td></tr>';

  try {
    const res = await fetch("/api/mediapatner-api?action=reports&limit=50");
    const data = await res.json();

    if (data.success && data.reports.length > 0) {
      tbody.innerHTML = data.reports.map((r) => `
        <tr>
          <td>#${r.id}</td>
          <td><strong>${r.institution_name || r.sender_name}</strong><br><small class="text-muted">@${r.sender_username || "-"}</small></td>
          <td>${r.created_at || "-"}</td>
          <td><span class="badge ${r.status === 'Diterima' ? 'badge-success' : 'badge-gold'}">${r.status}</span></td>
          <td>${r.processed_by_name || "Belum diproses"}</td>
          <td>
            <div style="display:flex;gap:4px;flex-wrap:wrap;">
              <button class="btn btn-sm btn-gold" onclick="sebarPosterDuluan(${r.poster_id})"><i class="fa-solid fa-rocket"></i> Sebar Duluan</button>
              <button class="btn btn-sm btn-dark" onclick="updateReport(${r.id}, 'Diterima')">✓ Terima</button>
              <button class="btn btn-sm btn-dark" onclick="updateReport(${r.id}, 'Ditolak')">✕ Tolak</button>
            </div>
          </td>
        </tr>
      `).join("");
    } else {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Belum ada laporan request poster.</td></tr>';
    }
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Gagal memuat laporan.</td></tr>';
  }
}

// Update Report Status
async function updateReport(reportId, newStatus) {
  try {
    const res = await fetch("/api/mediapatner-api", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "update_report_status",
        report_id: reportId,
        status: newStatus,
        admin_name: "Web Admin",
      }),
    });
    const data = await res.json();
    alert(data.message || "Status berhasil diperbarui");
    fetchReports();
  } catch (err) {
    alert("Gagal memperbarui status.");
  }
}

// Fetch Devices
async function fetchDevices() {
  const tbody = document.getElementById("devicesTableBody");
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" class="text-center">Memuat perangkat...</td></tr>';

  try {
    const res = await fetch("/api/mediapatner-api?action=devices");
    const data = await res.json();

    if (data.success && data.devices.length > 0) {
      tbody.innerHTML = data.devices.map((d) => `
        <tr>
          <td><code>${d.device_id.substring(0, 10)}...</code></td>
          <td>${d.admin_name}</td>
          <td>${d.phone_number}</td>
          <td>${d.device_model}</td>
          <td>${d.login_at}</td>
          <td><span class="badge badge-success">${d.status}</span></td>
        </tr>
      `).join("");
    } else {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Belum ada perangkat MTProto terdaftar. Silakan login via bot Telegram.</td></tr>';
    }
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Gagal memuat data perangkat.</td></tr>';
  }
}

// Diagnostics: Check Webhook Info
async function checkWebhookInfo() {
  const box = document.getElementById("webhookResult");
  box.classList.remove("hidden");
  box.textContent = "Memeriksa status webhook Telegram API...";

  try {
    const res = await fetch("/api/mediapatner-setup-webhook?action=info");
    const data = await res.json();
    box.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    box.textContent = "Error: " + err.message;
  }
}

// Diagnostics: Re-register Webhook
async function registerWebhook() {
  const box = document.getElementById("webhookResult");
  box.classList.remove("hidden");
  box.textContent = "Mendaftarkan webhook ke Telegram API...";

  try {
    const res = await fetch("/api/mediapatner-setup-webhook?action=setup");
    const data = await res.json();
    box.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    box.textContent = "Error: " + err.message;
  }
}

// Save New Report Chat
async function saveNewReportChat() {
  const input = document.getElementById("newReportChatInput");
  const chatId = input.value.trim();
  if (!chatId) return alert("Masukkan Chat ID terlebih dahulu.");

  try {
    const res = await fetch("/api/mediapatner-api", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "set_report_chat", chat_id: chatId }),
    });
    const data = await res.json();
    alert(data.message || "Chat tujuan diperbarui.");
    input.value = "";
    fetchSystemStatus();
  } catch (err) {
    alert("Gagal memperbarui chat tujuan.");
  }
}

// Trigger Manual Cron
async function triggerManualCron() {
  const box = document.getElementById("cronResult");
  box.classList.remove("hidden");
  box.textContent = "Menjalankan cron publikasi poster...";

  try {
    const res = await fetch("/api/cron/mediapatner-publish");
    const data = await res.json();
    box.textContent = JSON.stringify(data, null, 2);
    fetchSystemStatus();
  } catch (err) {
    box.textContent = "Error: " + err.message;
  }
}

// Sebar Poster Duluan (Publish Now / Early Broadcast)
async function sebarPosterDuluan(posterId) {
  if (!posterId) return alert("ID poster tidak valid.");
  const confirmMsg = confirm(`Apakah Anda yakin ingin menyebarkan poster #${posterId} sekarang ke channel @ASCHENEO tanpa menunggu jadwal resmi?`);
  if (!confirmMsg) return;

  try {
    const res = await fetch("/api/mediapatner-api", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "publish_now", poster_id: posterId }),
    });
    const data = await res.json();
    if (data.success) {
      alert("🚀 " + (data.message || `Poster #${posterId} berhasil disebar duluan ke channel @ASCHENEO!`));
      fetchPosters();
      fetchReports();
      fetchSystemStatus();
    } else {
      alert("❌ " + (data.error || "Gagal menyebarkan poster."));
    }
  } catch (err) {
    alert("Error: " + err.message);
  }
}

// Ping Broadcast Channel (@ASCHENEO)
async function pingBroadcastChannel() {
  const box = document.getElementById("pingChannelResult");
  if (!box) return;
  box.classList.remove("hidden");
  box.textContent = "📡 Menghubungi channel @ASCHENEO dan mengukur latensi Telegram API...";

  try {
    const res = await fetch("/api/mediapatner-api?action=ping_channel");
    const data = await res.json();
    box.textContent = JSON.stringify(data, null, 2);
    if (data.success) {
      alert(`✅ Ping Sukses!\nChannel: ${data.channel}\nJudul: ${data.chat_title}\nLatency: ${data.latency_ms} ms\nStatus: ${data.health_status}`);
    } else {
      alert(`⚠️ Ping Gagal: ${data.error || 'Tidak dapat terhubung ke channel'}`);
    }
  } catch (err) {
    box.textContent = "Error: " + err.message;
  }
}
