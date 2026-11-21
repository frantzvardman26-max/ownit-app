/* Vindie VPN: YouTube without ads, in the app's own player. Same methods as open-source browser ad blockers:
   1) strip the ad instructions out of YouTube's player data before the player reads them,
   2) hide ad boxes in the page, 3) if an ad still starts, mute it, jump to its end and press Skip.
   Runs only on youtube.com inside this app. Nothing is sent anywhere. */
(function () {
  if (window.__vvClean) return; window.__vvClean = 1;
  var KEYS = ['adPlacements', 'adSlots', 'playerAds', 'adBreakHeartbeatParams', 'adBreakParams'];
  function prune(o, d) {
    if (!o || typeof o !== 'object' || (d = d || 0) > 6) return o;
    for (var i = 0; i < KEYS.length; i++) if (KEYS[i] in o) { try { delete o[KEYS[i]]; } catch (e) {} }
    if (o.playerResponse) prune(o.playerResponse, d + 1);
    if (Array.isArray(o)) for (var j = 0; j < o.length && j < 50; j++) prune(o[j], d + 1);
    return o;
  }
  var P = JSON.parse; JSON.parse = function () { var r = P.apply(this, arguments); try { prune(r); } catch (e) {} return r; };
  var J = Response.prototype.json; Response.prototype.json = function () { return J.apply(this, arguments).then(function (r) { try { prune(r); } catch (e) {} return r; }); };
  ['ytInitialPlayerResponse', 'playerResponse'].forEach(function (k) {
    var v; try { Object.defineProperty(window, k, { configurable: true, get: function () { return v; }, set: function (x) { v = prune(x); } }); } catch (e) {}
  });
  var css = 'ytm-promoted-sparkles-web-renderer,ytm-promoted-video-renderer,ytm-companion-ad-renderer,ytm-companion-slot,ad-slot-renderer,'
    + 'ytm-ad-slot-renderer,ytd-ad-slot-renderer,ytd-in-feed-ad-layout-renderer,ytd-banner-promo-renderer,ytd-statement-banner-renderer,'
    + 'ytm-paid-content-overlay-renderer,#player-ads,.ytp-ad-module,.ytp-ad-overlay-container,ytm-mealbar-promo-renderer{display:none!important}';
  function addCss() { if (document.getElementById('vv-clean')) return; var s = document.createElement('style'); s.id = 'vv-clean'; s.textContent = css; (document.head || document.documentElement).appendChild(s); }
  if (document.documentElement) addCss(); document.addEventListener('DOMContentLoaded', addCss);
  setInterval(function () {
    addCss();
    var p = document.querySelector('.html5-video-player'), v = document.querySelector('video');
    if (p && v && (p.classList.contains('ad-showing') || p.classList.contains('ad-interrupting'))) {
      v.muted = true; if (isFinite(v.duration) && v.duration > 0) v.currentTime = v.duration;
      var b = document.querySelector('.ytp-ad-skip-button,.ytp-ad-skip-button-modern,.ytp-skip-ad-button,button[class*="skip"]'); if (b) b.click();
    } else if (v && v.muted && v.dataset.vvMuted) { v.muted = false; delete v.dataset.vvMuted; }
    if (p && v && p.classList.contains('ad-showing')) v.dataset.vvMuted = '1';
  }, 300);
})();
