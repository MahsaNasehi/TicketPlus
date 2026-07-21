(() => {
  'use strict';

  // Only this account gets the settings panel and the "add a new theater" admin panel.
  const ADMIN_EMAIL = 'rosenazeri83@gmail.com';

  /* ---------- config & state ---------- */
  const DEFAULT_API_BASE = 'http://localhost:8080';
  const state = {
    apiBase: localStorage.getItem('ticketplus.apiBase') || DEFAULT_API_BASE,
    auth: null, // { token, user: { id, email, name } }
    events: [], // loaded from the backend catalog, see loadEvents()
    activeEvent: null,
    selectedSeats: new Set(),
    lockedSeats: new Set(),  // PENDING on the server, owned by someone else (or us, before/after our own lock)
    bookedSeats: new Set(),  // CONFIRMED on the server — permanently sold
    reservation: null,
    countdownTimer: null,
    seatPollTimer: null,
    adminRows: [], // draft seating rows while the admin is composing a new event
  };

  /* ---------- helpers ---------- */
  const $ = (id) => document.getElementById(id);
  const fa = new Intl.NumberFormat('fa-IR');

  function idempotencyKey(prefix) {
    const rnd = (crypto.randomUUID && crypto.randomUUID()) ||
      `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    return `${prefix}-${rnd}`;
  }

  function toast(message, kind = '') {
    const el = $('toast');
    el.textContent = message;
    el.hidden = false;
    el.className = 'toast' + (kind ? ` toast--${kind}` : '');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => { el.hidden = true; }, 4200);
  }

  async function api(method, path, { body, idemKey, auth = true } = {}) {
    const headers = {};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (idemKey) headers['Idempotency-Key'] = idemKey;
    if (auth && state.auth) headers['Authorization'] = `Bearer ${state.auth.token}`;
    let response;
    try {
      response = await fetch(state.apiBase + path, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch (networkError) {
      throw { network: true, message: networkError.message };
    }
    let data = null;
    try { data = await response.json(); } catch (_) { /* empty body */ }
    if (!response.ok) {
      throw { status: response.status, data };
    }
    return data;
  }

  /* ---------- authentication ---------- */
  function loadAuth() {
    const raw = localStorage.getItem('ticketplus.auth');
    if (!raw) return null;
    try { return JSON.parse(raw); } catch (_) { return null; }
  }

  function saveAuth(auth) {
    state.auth = auth;
    if (auth) localStorage.setItem('ticketplus.auth', JSON.stringify(auth));
    else localStorage.removeItem('ticketplus.auth');
    updateAuthUI();
  }

  function isAdmin() {
    return !!(state.auth && state.auth.user && state.auth.user.email &&
      state.auth.user.email.toLowerCase() === ADMIN_EMAIL);
  }

  /* ---------- admin-only UI (settings panel + "add theater" panel) ---------- */
  function updateAdminUI() {
    const admin = isAdmin();
    $('settingsBtn').hidden = !admin;
    $('adminSection').hidden = !admin;
    if (!admin) {
      $('settingsPanel').hidden = true;
      $('adminForm').hidden = true;
    }
  }

  function updateAuthUI() {
    const loggedIn = !!state.auth;
    $('authSection').hidden = loggedIn;
    $('appMain').hidden = !loggedIn;
    $('userBadge').hidden = !loggedIn;
    if (loggedIn) {
      $('userName').textContent = state.auth.user.name;
    } else {
      $('eventSection').hidden = false;
      $('seatSection').hidden = true;
      $('ticketSection').hidden = true;
      stopSeatPolling();
      stopCountdown();
    }
    updateAdminUI();
  }

  function switchAuthTab(tab) {
    const isLogin = tab === 'login';
    $('tabLogin').classList.toggle('is-active', isLogin);
    $('tabRegister').classList.toggle('is-active', !isLogin);
    $('loginBox').hidden = !isLogin;
    $('registerBox').hidden = isLogin;
  }

  function describeAuthError(error, fallback) {
    if (error.network) return 'ارتباط با سرور برقرار نشد. لطفاً اتصال اینترنت خود را بررسی کنید.';
    if (error.data && error.data.message) return error.data.message;
    return fallback;
  }

  async function handleLogin(event) {
    event.preventDefault();
    const btn = $('loginSubmit');
    const note = $('loginNote');
    btn.disabled = true;
    note.textContent = '';
    note.className = 'auth-note';
    try {
      const result = await api('POST', '/auth/login', {
        body: { email: $('loginEmail').value.trim(), password: $('loginPassword').value },
        auth: false,
      });
      saveAuth(result);
      toast(`خوش آمدید، ${result.user.name}`, 'ok');
      loadEvents();
    } catch (error) {
      note.textContent = describeAuthError(error, 'ورود ناموفق بود.');
      note.className = 'auth-note auth-note--error';
    } finally {
      btn.disabled = false;
    }
  }

  async function handleRegister(event) {
    event.preventDefault();
    const btn = $('registerSubmit');
    const note = $('registerNote');
    btn.disabled = true;
    note.textContent = '';
    note.className = 'auth-note';
    try {
      const result = await api('POST', '/auth/register', {
        body: {
          name: $('registerName').value.trim(),
          email: $('registerEmail').value.trim(),
          password: $('registerPassword').value,
        },
        auth: false,
      });
      saveAuth(result);
      toast(`حساب شما ساخته شد. خوش آمدید، ${result.user.name}`, 'ok');
      loadEvents();
    } catch (error) {
      note.textContent = describeAuthError(error, 'ثبت‌نام ناموفق بود.');
      note.className = 'auth-note auth-note--error';
    } finally {
      btn.disabled = false;
    }
  }

  function handleLogout() {
    saveAuth(null);
    state.activeEvent = null;
    state.selectedSeats.clear();
    state.reservation = null;
    renderEvents();
    toast('از حساب خود خارج شدید.', '');
  }

  function initAuth() {
    state.auth = loadAuth();
    updateAuthUI();
    $('tabLogin').addEventListener('click', () => switchAuthTab('login'));
    $('tabRegister').addEventListener('click', () => switchAuthTab('register'));
    $('loginForm').addEventListener('submit', handleLogin);
    $('registerForm').addEventListener('submit', handleRegister);
    $('logoutBtn').addEventListener('click', handleLogout);
  }

  /* ---------- settings panel (admin-only) ---------- */
  function initSettings() {
    $('apiBaseInput').value = state.apiBase;
    $('settingsBtn').addEventListener('click', () => {
      $('settingsPanel').hidden = !$('settingsPanel').hidden;
    });
    $('apiBaseSave').addEventListener('click', () => {
      const value = $('apiBaseInput').value.trim().replace(/\/$/, '');
      if (!value) return;
      state.apiBase = value;
      localStorage.setItem('ticketplus.apiBase', value);
      toast('نشانی سرور ذخیره شد', 'ok');
      loadEvents();
    });
  }

  /* ---------- event catalog (GET/POST /events) ---------- */
  async function loadEvents() {
    try {
      const data = await api('GET', '/events');
      state.events = data.events || [];
      renderEvents();
    } catch (_) {
      // keep showing whichever list we already had; individual actions surface their own errors
    }
  }

  function rowPriceMap(event) {
    const map = {};
    (event.rows || []).forEach((row) => { map[row.label] = row.priceMinor; });
    return map;
  }

  function priceRangeLabel(event) {
    const prices = (event.rows || []).map((row) => row.priceMinor);
    if (!prices.length) return '';
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    return min === max
      ? `بلیت ${fa.format(min)} ریال`
      : `بلیت از ${fa.format(min)} تا ${fa.format(max)} ریال`;
  }

  function seatPrice(seatId) {
    if (!state.activeEvent) return 0;
    const rowLabel = seatId.split('-')[0];
    const row = (state.activeEvent.rows || []).find((r) => r.label === rowLabel);
    return row ? row.priceMinor : 0;
  }

  /* ---------- event picker ---------- */
  function renderEvents() {
    const row = $('eventRow');
    row.innerHTML = '';
    state.events.forEach((event) => {
      const card = document.createElement('button');
      card.className = 'event-card';
      card.type = 'button';
      card.dataset.eventId = event.id;
      card.classList.toggle('is-active', !!(state.activeEvent && state.activeEvent.id === event.id));
      card.innerHTML = `
        <span class="event-card__kicker">Live&nbsp;Booking</span>
        <h3 class="event-card__title">${event.title}</h3>
        <p class="event-card__meta">${event.venue}</p>
        <p class="event-card__meta">${event.dateLabel}</p>
        <div class="event-card__price">${priceRangeLabel(event)}</div>
      `;
      card.addEventListener('click', () => selectEvent(event));
      row.appendChild(card);
    });
  }

  function selectEvent(event) {
    state.activeEvent = event;
    state.selectedSeats.clear();
    state.lockedSeats.clear();
    state.bookedSeats.clear();
    state.reservation = null;
    stopCountdown();

    renderEvents();

    $('seatSection').hidden = false;
    $('ticketSection').hidden = true;
    $('reservationBox').hidden = true;
    $('lockBtn').hidden = false;
    $('lockBtn').disabled = true;
    $('lockNote').textContent = '';
    $('payBtn').disabled = false;
    $('payNote').textContent = '';
    $('payNote').className = 'form-note';
    renderSeatMap();
    renderSelection();
    refreshSeatStatus();
    startSeatPolling();
    $('seatSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /* ---------- live seat status (GET /events/:id/seats) ---------- */
  async function refreshSeatStatus() {
    if (!state.activeEvent) return;
    try {
      const status = await api('GET', `/events/${state.activeEvent.id}/seats`);
      state.bookedSeats = new Set(status.booked || []);
      // "locked" from the server includes our own pending reservation too;
      // renderSeatMap() tells those apart using state.reservation.seatIds.
      state.lockedSeats = new Set(status.locked || []);
      renderSeatMap();
    } catch (_) {
      // silent: a stale seat map is not worth interrupting the user over
    }
  }

  function startSeatPolling() {
    stopSeatPolling();
    state.seatPollTimer = setInterval(refreshSeatStatus, 4000);
  }

  function stopSeatPolling() {
    if (state.seatPollTimer) {
      clearInterval(state.seatPollTimer);
      state.seatPollTimer = null;
    }
  }

  /* ---------- seat map ---------- */
  function renderSeatMap() {
    const wrap = $('auditorium');
    const focusSeat = document.activeElement && document.activeElement.dataset
      ? document.activeElement.dataset.seat
      : null;
    wrap.innerHTML = '';
    const event = state.activeEvent;
    const prices = rowPriceMap(event);
    event.rows.forEach((row) => {
      const rowEl = document.createElement('div');
      rowEl.className = 'auditorium__row';
      const label = document.createElement('span');
      label.className = 'auditorium__rowlabel';
      label.textContent = row.label;
      rowEl.appendChild(label);
      for (let n = 1; n <= row.seats; n++) {
        const seatId = `${row.label}-${n}`;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'seat';
        btn.textContent = n;
        btn.dataset.seat = seatId;
        btn.title = `ردیف ${row.label} — ${fa.format(prices[row.label] || 0)} ریال`;
        applySeatVisual(btn, seatId);
        btn.addEventListener('click', () => toggleSeat(seatId, btn));
        rowEl.appendChild(btn);
        if (seatId === focusSeat) btn.focus();
      }
      wrap.appendChild(rowEl);
    });
  }

  function applySeatVisual(btn, seatId) {
    const isMine = !!(state.reservation && state.reservation.seatIds.includes(seatId));
    const isBooked = state.bookedSeats.has(seatId);
    const isLockedByOther = !isMine && state.lockedSeats.has(seatId);
    const isSelected = state.selectedSeats.has(seatId);

    btn.classList.toggle('is-booked', isBooked);
    btn.classList.toggle('is-mine', isMine && !isBooked);
    btn.classList.toggle('is-locked', isLockedByOther && !isBooked);
    btn.classList.toggle('is-selected', isSelected && !isMine && !isBooked && !isLockedByOther);
    btn.disabled = isBooked || isLockedByOther || isMine;
  }

  function toggleSeat(seatId, btn) {
    if (state.reservation) return; // locked already, no changes mid-flow
    if (state.bookedSeats.has(seatId) || state.lockedSeats.has(seatId)) return; // taken by someone else
    if (state.selectedSeats.has(seatId)) {
      state.selectedSeats.delete(seatId);
    } else {
      state.selectedSeats.add(seatId);
    }
    applySeatVisual(btn, seatId);
    renderSelection();
  }

  function renderSelection() {
    const chips = $('seatChips');
    const seats = [...state.selectedSeats].sort();
    chips.innerHTML = seats.length
      ? seats.map((s) => `<li class="seat-chip">${s} · ${fa.format(seatPrice(s))} ریال</li>`).join('')
      : '<li class="seat-chips__empty">هنوز صندلی‌ای انتخاب نکرده‌اید</li>';

    const total = seats.reduce((sum, s) => sum + seatPrice(s), 0);
    $('priceTotal').textContent = `${fa.format(total)} ریال`;
    $('lockBtn').disabled = seats.length === 0 || !!state.reservation;
  }

  /* ---------- lock seats (POST /reservations) ---------- */
  async function lockSeats() {
    const seats = [...state.selectedSeats];
    if (!seats.length || !state.auth) return;
    $('lockBtn').disabled = true;
    $('lockNote').textContent = 'در حال قفل کردن صندلی‌ها…';
    $('lockNote').className = 'form-note';
    try {
      const reservation = await api('POST', '/reservations', {
        body: { userId: state.auth.user.id, eventId: state.activeEvent.id, seatIds: seats },
        idemKey: idempotencyKey('reserve'),
      });
      state.reservation = reservation;
      state.lockedSeats = new Set([...state.lockedSeats, ...seats]);
      $('lockNote').textContent = '';
      $('lockBtn').hidden = true;
      $('reservationBox').hidden = false;
      $('payBtn').disabled = false;
      $('payNote').textContent = '';
      $('payNote').className = 'form-note';
      $('reservationId').textContent = reservation.id;
      startCountdown(reservation.expiresAt);
      renderSeatMap();
      toast('صندلی‌ها با موفقیت قفل شدند. اکنون می‌توانید پرداخت را انجام دهید.', 'ok');
    } catch (error) {
      $('lockBtn').disabled = false;
      if (error.network) {
        $('lockNote').textContent = 'ارتباط با سرور برقرار نشد. لطفاً دوباره تلاش کنید.';
      } else if (error.status === 409) {
        seats.forEach((seatId) => state.lockedSeats.add(seatId));
        state.selectedSeats.clear();
        renderSeatMap();
        renderSelection();
        $('lockNote').textContent = 'حداقل یکی از صندلی‌های انتخابی هم‌زمان توسط کاربر دیگری قفل شد. انتخاب پاک شد؛ صندلی‌های دیگری را امتحان کنید.';
      } else if (error.status === 404) {
        $('lockNote').textContent = 'این رویداد دیگر در دسترس نیست.';
      } else if (error.status === 400) {
        $('lockNote').textContent = `درخواست نامعتبر: ${error.data && error.data.message ? error.data.message : ''}`;
      } else {
        $('lockNote').textContent = 'خطای غیرمنتظره‌ای رخ داد. لطفاً دوباره تلاش کنید.';
      }
      $('lockNote').className = 'form-note form-note--error';
    }
  }

  /* ---------- countdown ---------- */
  function startCountdown(expiresAtIso) {
    stopCountdown();
    const expires = new Date(expiresAtIso).getTime();
    const tick = () => {
      const remainingMs = expires - Date.now();
      if (remainingMs <= 0) {
        stopCountdown();
        $('countdown').textContent = '۰۰:۰۰';
        onReservationExpired();
        return;
      }
      const totalSec = Math.floor(remainingMs / 1000);
      const mm = String(Math.floor(totalSec / 60)).padStart(2, '0');
      const ss = String(totalSec % 60).padStart(2, '0');
      $('countdown').textContent = `${mm}:${ss}`;
    };
    tick();
    state.countdownTimer = setInterval(tick, 1000);
  }

  function stopCountdown() {
    if (state.countdownTimer) {
      clearInterval(state.countdownTimer);
      state.countdownTimer = null;
    }
  }

  function onReservationExpired() {
    toast('مهلت رزرو به پایان رسید و صندلی‌ها آزاد شدند. لطفاً دوباره انتخاب کنید.', 'error');
    state.reservation = null;
    state.selectedSeats.clear();
    $('reservationBox').hidden = true;
    $('lockBtn').hidden = false;
    refreshSeatStatus();
    renderSelection();
  }

  /* ---------- checkout (POST /checkouts) ---------- */
  async function payAndIssue() {
    if (!state.reservation) return;
    const payBtn = $('payBtn');
    payBtn.disabled = true;
    $('payNote').textContent = 'در حال ارتباط با درگاه پرداخت…';
    $('payNote').className = 'form-note';

    const currency = $('currencySelect').value;
    const amountMinor = [...state.selectedSeats].reduce((sum, s) => sum + seatPrice(s), 0);

    try {
      const attempt = await api('POST', '/checkouts', {
        body: { reservationId: state.reservation.id, amountMinor, currency },
        idemKey: idempotencyKey('pay'),
      });

      if (attempt.status === 'SUCCEEDED') {
        stopCountdown();
        stopSeatPolling();
        const ticket = await api('GET', `/tickets/by-reservation/${state.reservation.id}`);
        showTicket(ticket);
      } else if (attempt.status === 'FAILED') {
        $('payNote').textContent = 'پرداخت ناموفق بود؛ صندلی‌ها آزاد شدند. لطفاً دوباره از ابتدا رزرو کنید.';
        $('payNote').className = 'form-note form-note--error';
        stopCountdown();
        state.reservation = null;
        state.selectedSeats.clear();
        $('reservationBox').hidden = true;
        $('lockBtn').hidden = false;
        refreshSeatStatus();
        renderSelection();
      } else {
        $('payNote').textContent = 'وضعیت پرداخت هنوز نامشخص است (در حال تطبیق). لطفاً کمی بعد دوباره تلاش کنید.';
        $('payNote').className = 'form-note form-note--warn';
        payBtn.disabled = false;
      }
    } catch (error) {
      payBtn.disabled = false;
      if (error.network) {
        $('payNote').textContent = 'ارتباط با سرور برقرار نشد.';
      } else if (error.status === 400) {
        $('payNote').textContent = `درخواست نامعتبر: ${error.data && error.data.message ? error.data.message : ''}`;
      } else {
        $('payNote').textContent = 'خطای غیرمنتظره‌ای هنگام تسویه حساب رخ داد.';
      }
      $('payNote').className = 'form-note form-note--error';
    }
  }

  /* ---------- ticket stub ---------- */
  function showTicket(ticket) {
    $('seatSection').hidden = true;
    $('ticketSection').hidden = false;
    $('stubEvent').textContent = state.activeEvent.title;
    $('stubVenue').textContent = state.activeEvent.venue;
    $('stubSeats').textContent = [...state.selectedSeats].sort().join('، ');
    $('stubReservation').textContent = state.reservation.id;
    $('stubTicketId').textContent = ticket.id;
    $('stubHash').textContent = ticket.qrHash;
    renderFauxQr(ticket.qrHash);
    $('ticketSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
    toast('بلیت با موفقیت صادر شد 🎟', 'ok');
  }

  function renderFauxQr(hash) {
    const grid = $('qrCode');
    grid.innerHTML = '';
    const chars = (hash || 'ticketplus').replace(/-/g, '');
    for (let i = 0; i < 64; i++) {
      const cell = document.createElement('div');
      const code = chars.charCodeAt(i % chars.length) || 0;
      const on = ((code + i * 7) % 5) < 2;
      // keep corners looking like finder patterns for a QR-ish silhouette
      const row = Math.floor(i / 8), col = i % 8;
      const isCorner = (row < 3 && col < 3) || (row < 3 && col > 4) || (row > 4 && col < 3);
      if (!on && !isCorner) cell.className = 'off';
      grid.appendChild(cell);
    }
  }

  /* ---------- admin: add a new theater/event ---------- */
  function defaultAdminRows() {
    return [
      { label: 'A', seats: 10, priceMinor: 500000 },
      { label: 'B', seats: 10, priceMinor: 400000 },
    ];
  }

  function renderAdminRows() {
    const wrap = $('adminRows');
    wrap.innerHTML = '';
    state.adminRows.forEach((row, index) => {
      const rowEl = document.createElement('div');
      rowEl.className = 'admin-row';
      rowEl.innerHTML = `
        <label>برچسب ردیف
          <input type="text" data-field="label" data-index="${index}" value="${row.label}">
        </label>
        <label>تعداد صندلی
          <input type="number" min="1" data-field="seats" data-index="${index}" value="${row.seats}">
        </label>
        <label>قیمت هر صندلی (ریال)
          <input type="number" min="1" step="1000" data-field="priceMinor" data-index="${index}" value="${row.priceMinor}">
        </label>
        <button type="button" class="admin-row__remove" data-remove="${index}" ${state.adminRows.length <= 1 ? 'disabled' : ''}>حذف</button>
      `;
      wrap.appendChild(rowEl);
    });

    wrap.querySelectorAll('input').forEach((input) => {
      input.addEventListener('input', () => {
        const index = Number(input.dataset.index);
        const field = input.dataset.field;
        state.adminRows[index][field] = field === 'label' ? input.value : Number(input.value);
      });
    });
    wrap.querySelectorAll('[data-remove]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const index = Number(btn.dataset.remove);
        if (state.adminRows.length <= 1) return;
        state.adminRows.splice(index, 1);
        renderAdminRows();
      });
    });
  }

  function addAdminRow() {
    const nextLabel = String.fromCharCode(65 + state.adminRows.length); // A, B, C, ...
    state.adminRows.push({ label: nextLabel, seats: 10, priceMinor: 300000 });
    renderAdminRows();
  }

  function resetAdminForm() {
    $('adminTitle').value = '';
    $('adminVenue').value = '';
    $('adminDate').value = '';
    state.adminRows = defaultAdminRows();
    renderAdminRows();
    $('adminNote').textContent = '';
    $('adminNote').className = 'form-note';
  }

  async function handleCreateEvent(event) {
    event.preventDefault();
    const btn = $('adminSubmitBtn');
    const note = $('adminNote');
    const title = $('adminTitle').value.trim();
    const venue = $('adminVenue').value.trim();
    const dateLabel = $('adminDate').value.trim();

    if (!title || !venue || !dateLabel) {
      note.textContent = 'عنوان، مکان و تاریخ الزامی است.';
      note.className = 'form-note form-note--error';
      return;
    }
    const rows = state.adminRows.map((row) => ({
      label: (row.label || '').toString().trim(),
      seats: Number(row.seats),
      priceMinor: Number(row.priceMinor),
    }));
    const rowsAreValid = rows.every((row) => row.label && Number.isInteger(row.seats) && row.seats > 0 &&
      Number.isInteger(row.priceMinor) && row.priceMinor > 0);
    if (!rowsAreValid) {
      note.textContent = 'برای هر ردیف، برچسب، تعداد صندلی و قیمت معتبر لازم است.';
      note.className = 'form-note form-note--error';
      return;
    }

    btn.disabled = true;
    note.textContent = 'در حال افزودن تئاتر…';
    note.className = 'form-note';
    try {
      const created = await api('POST', '/events', { body: { title, venue, dateLabel, rows } });
      toast(`«${created.title}» با موفقیت اضافه شد.`, 'ok');
      resetAdminForm();
      $('adminForm').hidden = true;
      await loadEvents();
      const fresh = state.events.find((e) => e.id === created.id) || created;
      selectEvent(fresh);
    } catch (error) {
      if (error.status === 403) {
        note.textContent = 'فقط حساب مدیر می‌تواند تئاتر جدید اضافه کند.';
      } else if (error.status === 400) {
        note.textContent = `اطلاعات نامعتبر: ${error.data && error.data.message ? error.data.message : ''}`;
      } else if (error.network) {
        note.textContent = 'ارتباط با سرور برقرار نشد.';
      } else {
        note.textContent = 'خطای غیرمنتظره‌ای رخ داد.';
      }
      note.className = 'form-note form-note--error';
    } finally {
      btn.disabled = false;
    }
  }

  function initAdmin() {
    state.adminRows = defaultAdminRows();
    renderAdminRows();
    $('adminToggleBtn').addEventListener('click', () => {
      const form = $('adminForm');
      form.hidden = !form.hidden;
    });
    $('adminAddRowBtn').addEventListener('click', addAdminRow);
    $('adminForm').addEventListener('submit', handleCreateEvent);
  }

  /* ---------- restart ---------- */
  function restart() {
    stopCountdown();
    stopSeatPolling();
    state.activeEvent = null;
    state.selectedSeats.clear();
    state.lockedSeats.clear();
    state.bookedSeats.clear();
    state.reservation = null;
    $('ticketSection').hidden = true;
    $('seatSection').hidden = true;
    renderEvents();
    $('eventSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /* ---------- wire up ---------- */
  document.addEventListener('DOMContentLoaded', () => {
    initAuth();
    initSettings();
    initAdmin();
    loadEvents();
    setInterval(loadEvents, 8000); // so newly-added theaters show up for everyone without a manual refresh
    switchAuthTab('login');
    $('lockBtn').addEventListener('click', lockSeats);
    $('payBtn').addEventListener('click', payAndIssue);
    $('restartBtn').addEventListener('click', restart);
  });
})();
