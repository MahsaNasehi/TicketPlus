(() => {
  'use strict';

  /* ---------- config & state ---------- */
  const DEFAULT_API_BASE = 'http://localhost:8080';
  const state = {
    apiBase: localStorage.getItem('ticketplus.apiBase') || DEFAULT_API_BASE,
    auth: null, // { token, user: { id, email, name } }
    events: [
      {
        id: 'shab-e-santoor',
        title: 'شب موسیقی سنتی ایرانی',
        venue: 'تالار وحدت، تهران',
        date: 'پنجشنبه ۳۰ مرداد — ساعت ۲۱:۰۰',
        priceMinor: 850000,
        rows: [
          { label: 'A', seats: 8 },
          { label: 'B', seats: 10 },
          { label: 'C', seats: 10 },
        ],
      },
      {
        id: 'khashm-o-hayahoo',
        title: 'نمایش «خشم و هیاهو»',
        venue: 'تئاتر شهر، سالن اصلی',
        date: 'جمعه ۷ شهریور — ساعت ۱۹:۳۰',
        priceMinor: 450000,
        rows: [
          { label: 'A', seats: 9 },
          { label: 'B', seats: 11 },
          { label: 'C', seats: 11 },
          { label: 'D', seats: 13 },
        ],
      },
      {
        id: 'concert-e-rock',
        title: 'کنسرت راک شهر',
        venue: 'مجموعه ورزشی آزادی',
        date: 'جمعه ۲۱ شهریور — ساعت ۲۰:۰۰',
        priceMinor: 1200000,
        rows: [
          { label: 'A', seats: 12 },
          { label: 'B', seats: 14 },
          { label: 'C', seats: 14 },
        ],
      },
    ],
    activeEvent: null,
    selectedSeats: new Set(),
    lockedSeats: new Set(),  // PENDING on the server, owned by someone else (or us, before/after our own lock)
    bookedSeats: new Set(),  // CONFIRMED on the server — permanently sold
    reservation: null,
    countdownTimer: null,
    seatPollTimer: null,
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

  /* ---------- connection indicator ---------- */
  async function checkConnection() {
    const dot = $('connDot');
    const label = $('connLabel');
    try {
      await api('GET', '/health/ready');
      dot.className = 'conn__dot ok';
      label.textContent = 'به بک‌اند متصل است';
    } catch (error) {
      dot.className = 'conn__dot bad';
      label.textContent = error.network
        ? 'اتصال برقرار نشد — نشانی API را بررسی کنید'
        : `بک‌اند پاسخ غیرمنتظره داد (${error.status})`;
    }
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
  }

  function switchAuthTab(tab) {
    const isLogin = tab === 'login';
    $('tabLogin').classList.toggle('is-active', isLogin);
    $('tabRegister').classList.toggle('is-active', !isLogin);
    $('loginBox').hidden = !isLogin;
    $('registerBox').hidden = isLogin;
  }

  function describeAuthError(error, fallback) {
    if (error.network) return 'اتصال به بک‌اند برقرار نشد. نشانی API را از ⚙ بررسی کنید.';
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
      checkConnection();
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
      checkConnection();
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
    [...$('eventRow').children].forEach((c) => c.classList.remove('is-active'));
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

  /* ---------- settings panel ---------- */
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
      toast('نشانی API ذخیره شد', 'ok');
      checkConnection();
    });
  }

  /* ---------- event picker ---------- */
  function renderEvents() {
    const row = $('eventRow');
    row.innerHTML = '';
    state.events.forEach((event) => {
      const card = document.createElement('button');
      card.className = 'event-card';
      card.type = 'button';
      card.innerHTML = `
        <span class="event-card__kicker">Live&nbsp;Booking</span>
        <h3 class="event-card__title">${event.title}</h3>
        <p class="event-card__meta">${event.venue}</p>
        <p class="event-card__meta">${event.date}</p>
        <div class="event-card__price">بلیت از ${fa.format(event.priceMinor)} ریال</div>
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

    [...$('eventRow').children].forEach((card, i) => {
      card.classList.toggle('is-active', state.events[i].id === event.id);
    });

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
      // silent: the connection indicator already surfaces backend outages
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
      ? seats.map((s) => `<li class="seat-chip">${s}</li>`).join('')
      : '<li class="seat-chips__empty">هنوز صندلی‌ای انتخاب نکرده‌اید</li>';

    const total = seats.length * (state.activeEvent ? state.activeEvent.priceMinor : 0);
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
        $('lockNote').textContent = 'اتصال به بک‌اند برقرار نشد. نشانی API را از ⚙ بررسی کنید.';
      } else if (error.status === 409) {
        seats.forEach((seatId) => state.lockedSeats.add(seatId));
        state.selectedSeats.clear();
        renderSeatMap();
        renderSelection();
        $('lockNote').textContent = 'حداقل یکی از صندلی‌های انتخابی هم‌زمان توسط کاربر دیگری قفل شد. انتخاب پاک شد؛ صندلی‌های دیگری را امتحان کنید.';
      } else if (error.status === 400) {
        $('lockNote').textContent = `درخواست نامعتبر: ${error.data && error.data.message ? error.data.message : ''}`;
      } else {
        $('lockNote').textContent = 'خطای غیرمنتظره از بک‌اند دریافت شد.';
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
    const amountMinor = state.selectedSeats.size * state.activeEvent.priceMinor;

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
        $('payNote').textContent = 'وضعیت پرداخت هنوز نامشخص است (در حال تطبیق با درگاه). لطفاً کمی بعد دوباره تلاش کنید.';
        $('payNote').className = 'form-note form-note--warn';
        payBtn.disabled = false;
      }
    } catch (error) {
      payBtn.disabled = false;
      if (error.network) {
        $('payNote').textContent = 'اتصال به بک‌اند برقرار نشد.';
      } else if (error.status === 400) {
        $('payNote').textContent = `درخواست نامعتبر: ${error.data && error.data.message ? error.data.message : ''}`;
      } else {
        $('payNote').textContent = 'خطای غیرمنتظره هنگام تسویه حساب.';
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
    [...$('eventRow').children].forEach((c) => c.classList.remove('is-active'));
    $('eventSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /* ---------- wire up ---------- */
  document.addEventListener('DOMContentLoaded', () => {
    initAuth();
    initSettings();
    renderEvents();
    checkConnection();
    setInterval(checkConnection, 15000);
    switchAuthTab('login');
    $('lockBtn').addEventListener('click', lockSeats);
    $('payBtn').addEventListener('click', payAndIssue);
    $('restartBtn').addEventListener('click', restart);
  });
})();