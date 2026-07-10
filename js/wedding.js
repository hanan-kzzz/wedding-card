'use strict';

/* ══════════════════════════════════════════
   WEDDING WEBSITE — JAVASCRIPT
   Mohammed Abdul Razak & Henna Shireen
   Nikah: Sunday, 12 July 2026, 9:30 AM IST
══════════════════════════════════════════ */

// ── Wedding date target ────────────────────
const WEDDING_DATE = new Date('2026-07-12T09:30:00+05:30');

// ── DOM refs ───────────────────────────────
const splash        = document.getElementById('splash');
const details       = document.getElementById('details');
const swipeTrack    = document.getElementById('swipeTrack');
const swipeThumb    = document.getElementById('swipeThumb');
const swipeLabel    = document.getElementById('swipeLabel');
const swipeFill     = document.getElementById('swipeFill');
const bgMusic       = document.getElementById('bgMusic');
const musicPill     = document.getElementById('musicPill');
const musicPillDet  = document.getElementById('musicPillDetails');

// ── State ──────────────────────────────────
let musicStarted = false;  // has audio.play() ever succeeded?
let musicMuted   = false;  // is it currently muted?

/* ════════════════════════════════════════════
   AUDIO UNLOCK — iOS Safari requires a play()
   call during a user gesture before any later
   play() will succeed. We trigger a silent
   play/pause on the very first touch so that
   by the time the swipe completes, the audio
   context is already unlocked.
════════════════════════════════════════════ */
(function unlockAudioOnFirstTouch() {
  if (!bgMusic) return;
  function unlock() {
    bgMusic.muted = true;
    bgMusic.play().then(() => {
      bgMusic.pause();
      bgMusic.currentTime = 0;
      bgMusic.muted = false;
    }).catch(() => {});
    document.removeEventListener('touchstart', unlock, true);
    document.removeEventListener('mousedown',  unlock, true);
  }
  document.addEventListener('touchstart', unlock, { capture: true, once: true, passive: true });
  document.addEventListener('mousedown',  unlock, { capture: true, once: true });
})();

/* ════════════════════════════════════════════
   COUNTDOWN TIMER
════════════════════════════════════════════ */
const cdDays  = document.getElementById('cd-days');
const cdHours = document.getElementById('cd-hours');
const cdMins  = document.getElementById('cd-mins');
const cdSecs  = document.getElementById('cd-secs');

function pad(n) { return String(Math.max(0, n)).padStart(2, '0'); }

function animateDigit(el, newVal) {
  if (el.textContent === newVal) return;
  el.classList.remove('flip');
  // Force reflow
  void el.offsetWidth;
  el.textContent = newVal;
  el.classList.add('flip');
}

function updateCountdown() {
  const now  = Date.now();
  const diff = WEDDING_DATE.getTime() - now;

  if (diff <= 0) {
    animateDigit(cdDays,  '00');
    animateDigit(cdHours, '00');
    animateDigit(cdMins,  '00');
    animateDigit(cdSecs,  '00');
    return;
  }

  const totalSecs = Math.floor(diff / 1000);
  const days  = Math.floor(totalSecs / 86400);
  const hours = Math.floor((totalSecs % 86400) / 3600);
  const mins  = Math.floor((totalSecs % 3600) / 60);
  const secs  = totalSecs % 60;

  animateDigit(cdDays,  pad(days));
  animateDigit(cdHours, pad(hours));
  animateDigit(cdMins,  pad(mins));
  animateDigit(cdSecs,  pad(secs));
}

updateCountdown();
setInterval(updateCountdown, 1000);

/* ════════════════════════════════════════════
   SWIPE-TO-ATTEND
════════════════════════════════════════════ */
(function initSwipe() {
  let isDragging = false;
  let startX     = 0;
  let currentX   = 0;
  let trackW, thumbW, maxTravel;

  function getGeometry() {
    trackW    = swipeTrack.offsetWidth;
    thumbW    = swipeThumb.offsetWidth;
    maxTravel = trackW - thumbW - 16; // 8px padding each side
  }

  function setThumbX(x) {
    x = Math.max(0, Math.min(x, maxTravel));
    currentX = x;
    const progress = x / maxTravel;

    swipeThumb.style.transform = `translateY(-50%) translateX(${x}px)`;
    swipeLabel.style.opacity = String(Math.max(0, 1 - progress * 2));
    swipeFill.style.width = `${progress * 100}%`;
    swipeTrack.style.border = `1px solid rgba(255,255,255,${0.25 + progress * 0.5})`;
  }

  function onDragStart(clientX) {
    getGeometry();
    isDragging = true;
    startX     = clientX - currentX;
    swipeThumb.style.transition = 'none';
    swipeFill.style.transition  = 'none';
    swipeTrack.style.cursor     = 'grabbing';
  }

  function onDragMove(clientX) {
    if (!isDragging) return;
    setThumbX(clientX - startX);
  }

  function onDragEnd() {
    if (!isDragging) return;
    isDragging = false;
    swipeTrack.style.cursor = '';

    if (currentX / maxTravel >= 0.78) {
      completeSwipe();
    } else {
      snapBack();
    }
  }

  function snapBack() {
    swipeThumb.style.transition = 'transform 0.45s cubic-bezier(0.32,0.72,0,1)';
    swipeFill.style.transition  = 'width 0.45s cubic-bezier(0.32,0.72,0,1)';
    swipeLabel.style.transition = 'opacity 0.3s';
    setThumbX(0);
    currentX = 0;
    swipeLabel.style.opacity = '1';
  }

  function completeSwipe() {
    getGeometry();
    swipeThumb.style.transition = 'transform 0.3s cubic-bezier(0.32,0.72,0,1)';
    swipeFill.style.transition  = 'width 0.3s ease';
    setThumbX(maxTravel);

    swipeTrack.classList.add('done');
    swipeLabel.style.opacity    = '0';
    swipeLabel.style.paddingLeft = '0';

    setTimeout(() => {
      swipeLabel.textContent   = 'See you there! ✓';
      swipeLabel.style.opacity = '1';
    }, 250);

    // ── Start music SYNCHRONOUSLY during user gesture ──────────
    // bgMusic.play() must be called within the touchend/mouseup
    // event handler — any setTimeout breaks the autoplay policy.
    if (bgMusic && !musicStarted) {
      bgMusic.volume = 0;
      bgMusic.play().then(() => {
        musicStarted = true;
        musicMuted   = false;
        updateMusicUI();
        fadeVolume(0, 0.55, 2000);
      }).catch(() => {
        // Autoplay blocked — user can tap the music pill to start
      });
    }

    // Page reveal can safely be deferred (it's UI only)
    setTimeout(revealDetails, 700);
  }

  // ── Touch events ───────────────────────────
  swipeThumb.addEventListener('touchstart', e => {
    e.preventDefault();
    onDragStart(e.touches[0].clientX);
  }, { passive: false });

  document.addEventListener('touchmove', e => {
    if (isDragging) {
      e.preventDefault();
      onDragMove(e.touches[0].clientX);
    }
  }, { passive: false });

  document.addEventListener('touchend', () => onDragEnd());

  // ── Mouse events (desktop) ─────────────────
  swipeThumb.addEventListener('mousedown', e => {
    e.preventDefault();
    onDragStart(e.clientX);
  });
  document.addEventListener('mousemove', e => {
    if (isDragging) onDragMove(e.clientX);
  });
  document.addEventListener('mouseup', () => onDragEnd());

  // Resize
  window.addEventListener('resize', () => {
    if (!swipeTrack.classList.contains('done')) { currentX = 0; }
  });
})();

/* ════════════════════════════════════════════
   PAGE TRANSITION — REVEAL DETAILS
════════════════════════════════════════════ */
function revealDetails() {
  details.classList.add('revealed');
  details.removeAttribute('aria-hidden');

  splash.classList.add('exit');
  setTimeout(() => { splash.style.visibility = 'hidden'; }, 900);

}

/* ════════════════════════════════════════════
   BACKGROUND MUSIC
════════════════════════════════════════════ */
function fadeVolume(from, to, durationMs) {
  const steps    = 40;
  const interval = durationMs / steps;
  const delta    = (to - from) / steps;
  let   current  = from;
  const timer    = setInterval(() => {
    current = Math.max(0, Math.min(1, current + delta));
    bgMusic.volume = current;
    if ((delta > 0 && current >= to) || (delta < 0 && current <= to)) {
      clearInterval(timer);
    }
  }, interval);
}

function toggleMusic() {
  if (!bgMusic) return;

  if (!musicStarted) {
    // Audio hasn't started yet (swipe not done / autoplay blocked)
    // This click IS a user gesture so play() will work here
    bgMusic.volume = 0;
    bgMusic.play().then(() => {
      musicStarted = true;
      musicMuted   = false;
      updateMusicUI();
      fadeVolume(0, 0.55, 1000);
    }).catch(() => {});
    return;
  }

  // Toggle mute / unmute (don't pause — keep buffer position)
  musicMuted    = !musicMuted;
  bgMusic.muted = musicMuted;
  updateMusicUI();
}

function updateMusicUI() {
  const isAudible = musicStarted && !musicMuted;
  const pills = [musicPill, musicPillDet].filter(Boolean);
  pills.forEach(p => {
    if (isAudible) {
      p.classList.add('playing');
      p.setAttribute('aria-label', 'Mute music');
    } else {
      p.classList.remove('playing');
      p.setAttribute('aria-label', 'Play Nikkah Nasheed');
    }
  });
}

if (musicPill)    musicPill.addEventListener('click', toggleMusic);
if (musicPillDet) musicPillDet.addEventListener('click', toggleMusic);

/* ════════════════════════════════════════════
   DOWNLOAD CARD BUTTON
════════════════════════════════════════════ */
async function downloadWeddingCard(btn) {
  const CARD_URL = 'assets/wedding-card.png';
  const FILENAME = 'Mohammed-Henna-WeddingCard.png';

  const origText = btn.textContent;
  btn.textContent = 'Downloading…';
  btn.disabled    = true;

  try {
    const res  = await fetch(CARD_URL);
    if (!res.ok) throw new Error('Card image not found');
    const blob = await res.blob();
    const file = new File([blob], FILENAME, { type: blob.type || 'image/png' });

    // Mobile: native share sheet (WhatsApp status, etc.)
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({
        files: [file],
        title: 'Mohammed & Henna — Wedding Card',
        text:  'You\'re invited! ✨'
      });
    } else {
      // Desktop / fallback: trigger download
      const url = URL.createObjectURL(blob);
      const a   = document.createElement('a');
      a.href     = url;
      a.download = FILENAME;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    }
  } catch {
    // Silently fail — card image may not be uploaded yet
  } finally {
    btn.textContent = origText;
    btn.disabled    = false;
  }
}

document.querySelectorAll('.download-btn:not(.disabled)').forEach(btn => {
  btn.addEventListener('click', () => downloadWeddingCard(btn));
});


/* ════════════════════════════════════════════
   HAPTIC FEEDBACK (PWA / Safari)
════════════════════════════════════════════ */
function vibrate(pattern) {
  if ('vibrate' in navigator) navigator.vibrate(pattern);
}

swipeThumb.addEventListener('touchstart', () => vibrate(10), { passive: true });

/* ════════════════════════════════════════════
   LUCIDE ICONS — initialise all data-lucide
════════════════════════════════════════════ */
if (typeof lucide !== 'undefined') lucide.createIcons();

/* ════════════════════════════════════════════
   TRANSPORT ACCORDION
════════════════════════════════════════════ */
(function initAccordion() {
  const items = document.querySelectorAll('.accordion-item');
  items.forEach(item => {
    const header = item.querySelector('.accordion-header');
    if (!header) return;
    header.addEventListener('click', () => {
      const isOpen = item.classList.contains('open');
      // Close all
      items.forEach(i => {
        i.classList.remove('open');
        i.querySelector('.accordion-header').setAttribute('aria-expanded', 'false');
      });
      // Open the clicked one if it was closed
      if (!isOpen) {
        item.classList.add('open');
        header.setAttribute('aria-expanded', 'true');
      }
    });
  });
})();

/* ════════════════════════════════════════════
   FACE RECOGNITION UPLOAD
════════════════════════════════════════════ */
(function initFaceRecognition() {
  const uploadImageBtn = document.getElementById('uploadImageBtn');
  const liveSelfieBtn = document.getElementById('liveSelfieBtn');
  const selfieUpload = document.getElementById('selfieUpload');
  const liveSelfieUpload = document.getElementById('liveSelfieUpload');
  const selfieResult = document.getElementById('selfieResult');

  if (!uploadImageBtn || !selfieUpload) return;

  uploadImageBtn.addEventListener('click', () => {
    selfieUpload.click();
  });

  const handleUpload = async (e, btn) => {
    const file = e.target.files[0];
    if (!file) return;

    // Show immediate feedback
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i data-lucide="loader" class="spin"></i> Preparing...';
    btn.disabled = true;
    selfieResult.style.display = 'block';
    selfieResult.innerHTML = 'Getting ready...';
    if (typeof lucide !== 'undefined') lucide.createIcons();

    // Downscale the image to fit comfortably in sessionStorage and speed up upload
    const reader = new FileReader();
    reader.onload = function(event) {
      const img = new Image();
      img.onload = function() {
        const canvas = document.createElement('canvas');
        const MAX_SIZE = 800;
        let w = img.width;
        let h = img.height;
        if (Math.max(w, h) > MAX_SIZE) {
          const scale = MAX_SIZE / Math.max(w, h);
          w *= scale;
          h *= scale;
        }
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, w, h);
        
        // Convert to highly compressed JPEG base64
        const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
        
        // Store in sessionStorage to pass to gallery.html
        try {
          sessionStorage.setItem('pendingSelfie', dataUrl);
          sessionStorage.removeItem('matchedPhotos'); // Clear old matches
          window.location.href = 'gallery.html'; // Instantly redirect
        } catch (err) {
          console.error("Storage error:", err);
          selfieResult.style.color = '#f87171';
          selfieResult.innerHTML = 'Image too large. Please use a smaller file.';
          btn.innerHTML = originalText;
          btn.disabled = false;
        }
      };
      img.src = event.target.result;
    };
    reader.onerror = function() {
      selfieResult.style.color = '#f87171';
      selfieResult.innerHTML = 'Failed to read image file.';
      btn.innerHTML = originalText;
      btn.disabled = false;
    };
    reader.readAsDataURL(file);
    e.target.value = ''; // clear input
  };

  selfieUpload.addEventListener('change', (e) => handleUpload(e, uploadImageBtn));
})();

/* ════════════════════════════════════════════
   LIVE CAMERA MODAL
════════════════════════════════════════════ */
(function initCameraModal() {
  const liveSelfieBtn = document.getElementById('liveSelfieBtn');
  const cameraModal = document.getElementById('cameraModal');
  const closeCameraBtn = document.getElementById('closeCameraBtn');
  const cameraVideo = document.getElementById('cameraVideo');
  const captureBtn = document.getElementById('captureBtn');
  const cameraCanvas = document.getElementById('cameraCanvas');
  const selfieResult = document.getElementById('selfieResult');
  
  let stream = null;
  
  if (!liveSelfieBtn || !cameraModal) return;

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      stream = null;
    }
    cameraVideo.srcObject = null;
    cameraModal.setAttribute('aria-hidden', 'true');
  };

  const startCamera = async () => {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
      cameraVideo.srcObject = stream;
      cameraModal.setAttribute('aria-hidden', 'false');
    } catch (err) {
      console.error("Camera error:", err);
      alert("Could not access camera. Please upload an image instead.");
    }
  };

  liveSelfieBtn.addEventListener('click', (e) => {
    e.preventDefault();
    startCamera();
  });

  closeCameraBtn.addEventListener('click', stopCamera);

  captureBtn.addEventListener('click', () => {
    if (!stream) return;
    
    // Draw to canvas
    cameraCanvas.width = cameraVideo.videoWidth;
    cameraCanvas.height = cameraVideo.videoHeight;
    const ctx = cameraCanvas.getContext('2d');
    
    // Mirror the canvas context since the video is mirrored
    ctx.translate(cameraCanvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(cameraVideo, 0, 0, cameraCanvas.width, cameraCanvas.height);
    
    // Convert to dataUrl and resize if needed (simplified resize inline)
    const MAX_SIZE = 800;
    let w = cameraCanvas.width;
    let h = cameraCanvas.height;
    if (Math.max(w, h) > MAX_SIZE) {
      const scale = MAX_SIZE / Math.max(w, h);
      w *= scale;
      h *= scale;
    }
    
    const finalCanvas = document.createElement('canvas');
    finalCanvas.width = w;
    finalCanvas.height = h;
    const finalCtx = finalCanvas.getContext('2d');
    finalCtx.drawImage(cameraCanvas, 0, 0, w, h);
    
    const dataUrl = finalCanvas.toDataURL('image/jpeg', 0.8);
    
    // Process upload UI
    const originalText = liveSelfieBtn.innerHTML;
    liveSelfieBtn.innerHTML = '<i data-lucide="loader" class="spin"></i> Preparing...';
    liveSelfieBtn.disabled = true;
    selfieResult.style.display = 'block';
    selfieResult.innerHTML = 'Getting ready...';
    if (typeof lucide !== 'undefined') lucide.createIcons();
    
    stopCamera();
    
    // Store and redirect
    try {
      sessionStorage.setItem('pendingSelfie', dataUrl);
      sessionStorage.removeItem('matchedPhotos');
      window.location.href = 'gallery.html';
    } catch (err) {
      console.error("Storage error:", err);
      selfieResult.style.color = '#f87171';
      selfieResult.innerHTML = 'Image too large. Please use a smaller file.';
      liveSelfieBtn.innerHTML = originalText;
      liveSelfieBtn.disabled = false;
    }
  });
})();
