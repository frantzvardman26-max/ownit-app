// Does the Vindie VPN YouTube cleanup strip ad instructions from a real watch page? Compares with and without it.
const { chromium, devices } = require('playwright');
const fs = require('fs'); const clean = fs.readFileSync(__dirname + '/yt-clean.js', 'utf8');
const vids = (process.env.VIDS || 'jNQXAC9IVRw,dQw4w9WgXcQ,kJQP7kiw5Fk').split(',');
(async () => {
  const b = await chromium.launch();
  for (const withClean of [false, true]) {
    const ctx = await b.newContext({ ...devices['Pixel 7'], locale: 'en-US' });
    await ctx.addCookies([{ name: 'SOCS', value: 'CAI', domain: '.youtube.com', path: '/' }]);   // decline the cookie banner
    if (withClean) await ctx.addInitScript(clean);
    let adReq = 0, playerAds = 0;
    ctx.on('request', r => { if (/\/pagead\/|\/api\/stats\/ads|get_midroll_info|doubleclick\.net/.test(r.url())) adReq++; });
    for (const v of vids) {
      const pg = await ctx.newPage();
      pg.on('response', async r => { if (/youtubei\/v1\/player/.test(r.url())) { try { const j = await r.json(); if (j.adPlacements || j.playerAds) playerAds++; } catch (e) {} } });
      try { await pg.goto('https://m.youtube.com/watch?v=' + v, { waitUntil: 'domcontentloaded', timeout: 45000 }); await pg.waitForTimeout(9000); } catch (e) { console.log(v, 'load error', e.message.slice(0, 80)); }
      const r = await pg.evaluate(() => { const p = window.ytInitialPlayerResponse; const pl = document.querySelector('.html5-video-player');
        return { title: document.title.slice(0, 40), hasIPR: !!p, adPlacements: !!(p && p.adPlacements), playerAds: !!(p && p.playerAds), adShowing: !!(pl && pl.classList.contains('ad-showing')), bot: /confirm you.re not a bot|unusual traffic/i.test(document.body.innerText) }; }).catch(e => ({ err: e.message.slice(0, 60) }));
      console.log((withClean ? 'WITH cleanup   ' : 'WITHOUT cleanup'), v, JSON.stringify(r));
      await pg.close();
    }
    console.log((withClean ? 'WITH' : 'WITHOUT'), 'ad requests seen:', adReq, '· player data carrying ads:', playerAds);
    await ctx.close();
  }
  await b.close();
})();
