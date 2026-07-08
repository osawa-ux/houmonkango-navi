(function() {
  'use strict';

  var ENDPOINT = 'https://zaitaku-members.vercel.app/api/analytics/event';
  var _lastSent = {};  // dedup: "clinicId:eventType" -> timestamp

  // <meta name="zm-clinic-id"> から clinic_id を取得
  function getClinicId() {
    var m = document.querySelector('meta[name="zm-clinic-id"]');
    return m ? m.getAttribute('content') : '';
  }

  // 同一ページ内の同一イベントを 1000ms 以内に重複送信しない
  function isDuplicate(clinicId, eventType) {
    var key = clinicId + ':' + eventType;
    var now = Date.now();
    if (_lastSent[key] && now - _lastSent[key] < 1000) return true;
    _lastSent[key] = now;
    return false;
  }

  function trackEvent(clinicId, eventType, sourcePage, metadata) {
    if (!clinicId || !eventType) return;
    if (isDuplicate(clinicId, eventType)) return;
    var payload = JSON.stringify({
      clinic_id: clinicId,
      event_type: eventType,
      source_page: sourcePage || window.location.pathname,
      metadata: metadata || {}
    });
    try {
      if (navigator.sendBeacon) {
        var blob = new Blob([payload], {type: 'application/json'});
        navigator.sendBeacon(ENDPOINT, blob);
      } else {
        fetch(ENDPOINT, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: payload,
          keepalive: true
        }).catch(function(){});
      }
    } catch(e) {}
  }

  // グローバル公開（詳細ページ・一覧ページで呼び出し可能）
  window.zmTrack = trackEvent;

  document.addEventListener('DOMContentLoaded', function() {
    var clinicId = getClinicId();

    // --- 詳細ページ専用処理 ---
    if (document.querySelector('.zm-detail-page')) {
      // ページビュー（1回のみ）
      if (clinicId) trackEvent(clinicId, 'clinic_profile_view', null, {});

      // 電話クリック
      document.querySelectorAll('a[href^="tel:"]').forEach(function(a) {
        a.addEventListener('click', function() {
          trackEvent(clinicId, 'phone_click', null, {});
        });
      });

      // 問い合わせクリック（通常 + ケアマネ + 退院支援）
      document.querySelectorAll('[data-event="inquiry_click"]').forEach(function(el) {
        el.addEventListener('click', function() {
          trackEvent(clinicId, 'inquiry_click', null, {});
        });
      });
      document.querySelectorAll('[data-event="care_manager_inquiry_click"]').forEach(function(el) {
        el.addEventListener('click', function() {
          trackEvent(clinicId, 'care_manager_inquiry_click', null, {});
        });
      });
      document.querySelectorAll('[data-event="discharge_support_inquiry_click"]').forEach(function(el) {
        el.addEventListener('click', function() {
          trackEvent(clinicId, 'discharge_support_inquiry_click', null, {});
        });
      });

      // premium_content セクションが viewport に入ったら premium_section_view
      var premiumSection = document.getElementById('zm-premium-content');
      if (premiumSection && window.IntersectionObserver) {
        var observed = false;
        var obs = new IntersectionObserver(function(entries) {
          entries.forEach(function(entry) {
            if (entry.isIntersecting && !observed) {
              observed = true;
              trackEvent(clinicId, 'premium_section_view', null, {});
              obs.disconnect();
            }
          });
        }, {threshold: 0.2});
        obs.observe(premiumSection);
      }
    }

    // --- 市区町村・都道府県ページ: カードクリック計測 ---
    document.querySelectorAll('.clinic-card[data-clinic-id]').forEach(function(card) {
      var cid = card.getAttribute('data-clinic-id');
      if (!cid) return;
      card.addEventListener('click', function(e) {
        // カード内リンクのクリックも捕捉
        trackEvent(cid, 'city_card_click', window.location.pathname, {});
        // GA4 へも送信（clinic_id は city ページでは個別クリニック不要のため省略）
        (window.gev||function(){})('city_card_click', {});
      }, true);
    });
  });
})();
