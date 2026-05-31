/* ===== MedFlow wireframe renderer ===== */
(function () {
  const MF = window.MF;
  const S = { dir: "B", page: "home", role: "patient" }; // state

  // ---------- tiny helpers ----------
  const gb = (label, cls = "") => `<div class="greybox ${cls}"><span>${label}</span></div>`;
  const annot = (txt) => `<div class="annot">↳ ${txt}</div>`;
  const secLabel = (t) => `<div class="sec-label">${t}</div>`;
  const roleChip = () =>
    S.role === "patient"
      ? `<span class="chip patient">● Patient view</span>`
      : `<span class="chip clinician">● Clinician view</span>`;

  // =====================================================
  //  NAV CHROME PER DIRECTION
  // =====================================================
  function navA() {
    const links = Object.keys(MF.mega)
      .map(
        (k) =>
          `<a class="has-mega" data-act="mega" data-val="${k}">${k} <span class="car">▼</span></a>`
      )
      .join("");
    const megas = Object.entries(MF.mega)
      .map(([k, v]) => {
        const cols = v.cols
          .map((c) =>
            c.feature
              ? `<div>${gb(c.feature, "tall")}</div>`
              : `<div><h4>${c.h}</h4><ul>${c.items
                  .map((i) => `<li>${i}</li>`)
                  .join("")}</ul></div>`
          )
          .join("");
        return `<div class="mega" data-mega="${k}"><div class="cols">${cols}</div></div>`;
      })
      .join("");
    return `
    <div class="navA">
      <div class="row">
        <div class="brand"><span class="mark"></span>${MF.brand}</div>
        <div class="navlinks">${links}</div>
        <div class="navutil">
          <a>Get pricing</a>
          <a>Help ▾</a>
          <div class="navrel">
            <a data-act="login">Login ▾</a>
            <div class="login-pop" data-login>
              <div class="lp-opt p" data-act="role" data-val="patient"><div class="ic">🧑</div><div><b>Patient login</b><small>Members & families</small></div></div>
              <div class="lp-opt c" data-act="role" data-val="clinician"><div class="ic">⚕</div><div><b>Clinician login</b><small>Care providers & staff</small></div></div>
            </div>
          </div>
          <span class="btn primary sm">Book a demo</span>
        </div>
      </div>
      ${megas}
    </div>`;
  }

  function navB() {
    const seg = `
      <div class="roleseg">
        <button class="${S.role === "patient" ? "on p" : ""}" data-act="role" data-val="patient">I'm a patient</button>
        <button class="${S.role === "clinician" ? "on c" : ""}" data-act="role" data-val="clinician">I'm a clinician</button>
      </div>`;
    const patientLinks = ["Find care", "Programs", "How it works", "Help"];
    const clinLinks = ["Join the network", "Tools", "Scheduling", "Resources"];
    const links = (S.role === "patient" ? patientLinks : clinLinks)
      .map((l) => `<a>${l}</a>`)
      .join("");
    return `
    <div class="rolebar">
      <span class="who">First — who are you?</span>
      ${seg}
      <span style="opacity:.6;font-size:12px;">nav & content adapt to your answer</span>
    </div>
    <div class="navB">
      <div class="row">
        <div class="brand"><span class="mark"></span>${MF.brand}</div>
        <div class="navlinks">${links}</div>
        <span class="btn sm">Login</span>
        <span class="btn primary sm">${S.role === "patient" ? "Get started" : "Apply to join"}</span>
      </div>
    </div>`;
  }

  function railC(body) {
    const items = [
      { v: "home", ic: "⌂", t: "Home" },
      { v: "eap", ic: "❤", t: "EAP" },
      { v: "pricing", ic: "$", t: "Plans" },
      { v: "more", ic: "▦", t: "More" },
    ];
    const rail = items
      .map(
        (i) =>
          `<div class="ritem ${S.page === i.v ? "on" : ""}" data-act="nav" data-val="${i.v}">${i.ic}<small>${i.t}</small></div>`
      )
      .join("");
    const pill =
      S.role === "patient"
        ? `<div class="rolepill p" data-act="role" data-val="clinician">🧑<br>Patient</div>`
        : `<div class="rolepill c" data-act="role" data-val="patient">⚕<br>Clinic</div>`;
    return `
    <div class="railwrap">
      <div class="rail">
        <div class="rmark"></div>
        ${rail}
        <div class="spring"></div>
        ${pill}
      </div>
      <div class="railmain">
        <div class="cmdbar">
          <div class="cmd">🔍 Search care, programs, docs… <span class="k">⌘K</span></div>
          <div class="cmd-util"><a>Book a demo</a><a>Login ▾</a></div>
        </div>
        ${body}
      </div>
    </div>`;
  }

  // =====================================================
  //  HERO (calm / clinical) — varies by direction & page
  // =====================================================
  function roleButtons() {
    return `
      <div class="btnrow" style="margin-top:14px;">
        <span class="btn ${S.role === "patient" ? "primary" : ""} sm" data-act="role" data-val="patient">🧑 I'm a patient</span>
        <span class="btn ${S.role === "clinician" ? "primary" : ""} sm" data-act="role" data-val="clinician">⚕ I'm a clinician</span>
      </div>
      ${annot("role chooser sits inside the hero, not hidden in a menu")}`;
  }

  function heroHome() {
    if (S.dir === "B") {
      // role-first: two doors
      return `<div class="wf-section">${secLabel("hero · role-first")}
        <p class="eyebrow">Virtual care, two clear front doors</p>
        <h1 class="wf">Clinical-grade care, calmly delivered.</h1>
        <p class="wf">Pick the door that's yours. ${MF.brand} reshapes everything below it — copy, CTAs and navigation — around whether you give or receive care.</p>
        <div class="doors" style="margin-top:18px;">
          <div class="door p" style="${S.role === "patient" ? "" : "opacity:.5"}">
            <span class="chip patient">For patients</span>
            <h3 class="wf" style="margin-top:10px;">Get care in minutes</h3>
            <p class="wf" style="font-size:14px;">Mental health, primary care & wellness — whenever courage finally strikes.</p>
            <span class="btn primary sm" data-act="role" data-val="patient">Find care →</span>
          </div>
          <div class="door c" style="${S.role === "clinician" ? "" : "opacity:.5"}">
            <span class="chip clinician">For clinicians</span>
            <h3 class="wf" style="margin-top:10px;">Practice without the noise</h3>
            <p class="wf" style="font-size:14px;">Flexible scheduling, calm tooling and a panel that respects your time.</p>
            <span class="btn primary sm" data-act="role" data-val="clinician">Join the network →</span>
          </div>
        </div>
        ${annot("entry IS the choice — the page commits to one audience immediately")}
      </div>`;
    }
    // A & C: standard calm clinical hero with split visual
    return `<div class="wf-section">${secLabel("hero · calm clinical")}
      <div class="split">
        <div>
          <p class="eyebrow">Virtual care for every employee</p>
          <h1 class="wf">Clinical-grade care, calmly delivered.</h1>
          <p class="wf">${MF.brand} connects your people to licensed clinicians in minutes — mental health, primary care and everyday wellness, in one quietly trusted platform.</p>
          <div class="btnrow"><span class="btn primary">See it in action</span><span class="btn">Book a call</span></div>
          ${roleButtons()}
        </div>
        <div>${gb("calm product still — clinician + member", "tall")}</div>
      </div>
    </div>`;
  }

  // =====================================================
  //  SHARED PAGE SECTIONS
  // =====================================================
  function logosSec() {
    return `<div class="wf-section">${secLabel("social proof")}
      <h2 class="wf" style="font-size:24px;">Trusted by 52,000+ organizations</h2>
      <div class="logos" style="margin-top:14px;">${MF.logos.map((l) => gb(l)).join("")}</div>
    </div>`;
  }

  function benefitsSec() {
    return `<div class="wf-section tint">${secLabel("benefits · carousel")}
      <h2 class="wf">Experience the ${MF.brand} difference</h2>
      <p class="wf muted">Satisfaction, utilization and wait-time guarantees — slide ◂ ▸</p>
      <div class="grid g3" style="margin-top:16px;">
        ${MF.benefits
          .map(
            (b) => `<div class="card">${gb(b.img, "tall")}
            <h3 class="wf" style="margin-top:12px;">${b.t}</h3>
            <ul style="margin:0;padding-left:18px;font-size:13px;color:#3f3e39;">${b.m
              .map((x) => `<li>${x}</li>`)
              .join("")}</ul></div>`
          )
          .join("")}
      </div>
    </div>`;
  }

  function programsSec() {
    const tabs = MF.programs
      .map(
        (p, i) =>
          `<span class="chip ${i === 0 ? "" : ""}" style="${i === 0 ? "background:var(--accent);color:#fff;border-color:var(--ink);" : ""}">${p.t}</span>`
      )
      .join("");
    return `<div class="wf-section">${secLabel("platform · tabs")}
      <h2 class="wf">${MF.brand}'s Integrated Care Platform</h2>
      <p class="wf muted">One care hub, 24/7/365 — programs that are stronger together.</p>
      <div style="display:flex;gap:10px;flex-wrap:wrap;margin:14px 0 20px;">${tabs}</div>
      <div class="split">
        <div>
          <h3 class="wf">${MF.programs[0].t}</h3>
          <p class="wf">${MF.programs[0].d}</p>
          <ul style="font-size:13px;color:#3f3e39;">
            <li>Digital intake & triage</li><li>Counsellor matching</li><li>Work–life resources</li>
          </ul>
          <span class="btn sm">Learn more →</span>
        </div>
        <div style="display:flex;gap:14px;justify-content:center;">
          ${gb(MF.programs[0].shot, "phone")}
          ${gb("detail screen", "phone")}
        </div>
      </div>
    </div>`;
  }

  function statsSec() {
    return `<div class="wf-section warm">${secLabel("impact · 3-col")}
      <h2 class="wf">Having real impact.</h2>
      <div class="grid g3" style="margin-top:18px;">
        ${MF.stats
          .map(
            (s) => `<div class="stat"><div class="num">${s.n}</div><div class="lab">${s.l}</div></div>`
          )
          .join("")}
      </div>
    </div>`;
  }

  function testiSec() {
    return `<div class="wf-section">${secLabel("testimonials · carousel")}
      <h2 class="wf">Over 26,000 five-star app ratings</h2>
      <div class="grid g2" style="margin-top:16px;">
        ${MF.testimonials
          .map(
            (t) => `<div class="card alt"><div style="font-size:15px;color:#3f3e39;">"${t.q}"</div>
            <div style="margin-top:10px;font-family:var(--font-hand);font-size:17px;">— ${t.a} <span class="muted" style="font-size:13px;">★★★★★</span></div></div>`
          )
          .join("")}
      </div>
      <div style="text-align:center;margin-top:14px;" class="muted">● ● ● ○ ○</div>
    </div>`;
  }

  function roiBanner() {
    return `<div class="wf-section tint">${secLabel("lead magnet")}
      <div class="split">
        <div>
          <h2 class="wf">The cost-benefit analysis your leadership needs to see.</h2>
          <p class="wf">Discover <b>13× the ROI</b>: the business case for virtual mental-health care.</p>
          <span class="btn primary">Download the report</span>
        </div>
        <div>${gb("report cover + HR leader", "tall")}</div>
      </div>
    </div>`;
  }

  function ctaBanner(t) {
    return `<div class="wf-section warm">${secLabel("cta banner")}
      <div style="text-align:center;">
        <h2 class="wf">${t}</h2>
        <div class="btnrow" style="justify-content:center;"><span class="btn primary">Book a demo</span><span class="btn">Talk to sales</span></div>
      </div>
    </div>`;
  }

  function footer() {
    const cols = {
      Platform: ["Integrated Care", "EAP", "Mental Health+", "Primary Care", "Wellness"],
      Company: ["About", "Careers", "Press", "Culture"],
      Resources: ["Blog", "Help centre", "Status", "Contact"],
      Apps: ["iOS app", "Android app", "Clinician portal", "API"],
    };
    return `<div class="wf-foot"><div class="cols">
      <div><div class="fbrand">${MF.brand}</div><p style="font-size:12px;opacity:.6;max-width:24ch;">Calm, clinical virtual care for every employee.</p></div>
      ${Object.entries(cols)
        .map(
          ([h, items]) =>
            `<div><h4>${h}</h4><ul>${items.map((i) => `<li>${i}</li>`).join("")}</ul></div>`
        )
        .join("")}
    </div>
    <div style="margin-top:20px;font-size:11px;opacity:.5;border-top:1px solid rgba(246,244,238,.2);padding-top:12px;">© 2026 ${MF.brand} · Privacy · Terms · AODA · Cookies</div>
    </div>`;
  }

  // =====================================================
  //  PAGE BODIES
  // =====================================================
  function pageHome() {
    return heroHome() + logosSec() + benefitsSec() + programsSec() + statsSec() + testiSec() + roiBanner() + footer();
  }

  function pageEAP() {
    const included = [
      ["Confidential counselling", "Phone, chat or video — same-day."],
      ["Work–life services", "Legal, financial & family referrals."],
      ["Manager support", "Coaching for difficult conversations."],
      ["Crisis response", "24/7 lines + on-site response."],
      ["Self-guided toolkits", "CBT modules & resilience content."],
      ["Reporting", "Aggregate utilization for HR."],
    ];
    const steps = [
      ["Reach out", "Member opens the app and describes what's going on — no gatekeeping forms."],
      ["Get matched", "Smart triage routes to the right counsellor or service in minutes."],
      ["Follow through", "Ongoing care plan, reminders and resources keep momentum going."],
    ];
    return `
    <div class="wf-section">${secLabel("eap · hero")}
      <div class="split">
        <div>
          <p class="eyebrow">Employee Assistance Program</p>
          <h1 class="wf">The EAP people actually use.</h1>
          <p class="wf">Outdated EAPs gather dust. ${MF.brand}'s is digital-first, employee-designed and built for the moment someone finally reaches out.</p>
          <div class="btnrow"><span class="btn primary">See it in action</span><span class="btn">Download overview</span></div>
          ${S.dir !== "B" ? roleButtons() : annot("CTA already tailored to " + S.role + " by the role bar above")}
        </div>
        <div>${gb("EAP app — services screen", "tall")}</div>
      </div>
    </div>
    <div class="wf-section tint">${secLabel("what's included")}
      <h2 class="wf">What's included</h2>
      <div class="grid g3" style="margin-top:16px;">
        ${included
          .map(
            ([t, d]) => `<div class="card"><h3 class="wf">${t}</h3><p class="wf" style="font-size:13px;margin:0;">${d}</p></div>`
          )
          .join("")}
      </div>
    </div>
    <div class="wf-section">${secLabel("how it works")}
      <h2 class="wf">How it works</h2>
      <div class="steps" style="margin-top:16px;">
        ${steps
          .map(
            ([t, d], i) => `<div class="step"><div class="n">${i + 1}</div><h3 class="wf">${t}</h3><p class="wf" style="font-size:13px;">${d}</p></div>`
          )
          .join("")}
      </div>
    </div>
    ${statsSec()}
    ${ctaBanner("Give your people an EAP worth opening.")}
    ${footer()}`;
  }

  function pagePricing() {
    const plans = [
      { n: "Essential", p: "$6", feat: false, items: ["EAP + crisis lines", "Self-guided toolkits", "Mobile + web apps", "Standard reporting"] },
      { n: "Plus", p: "$11", feat: true, items: ["Everything in Essential", "Mental Health+ program", "Primary care visits", "Dedicated success manager"] },
      { n: "Complete", p: "$16", feat: false, items: ["Everything in Plus", "Wellness + challenges", "Women's & family health", "Custom integrations & API"] },
    ];
    const rows = [
      ["EAP & crisis support", "✓", "✓", "✓"],
      ["Mental Health+", "—", "✓", "✓"],
      ["Primary care", "—", "✓", "✓"],
      ["Wellness program", "—", "—", "✓"],
      ["Reporting dashboards", "Basic", "Advanced", "Custom"],
    ];
    const faqs = ["Is there a per-use fee for members?", "How fast is implementation?", "Can we add programs later?", "Do you support unionized workforces?"];
    return `
    <div class="wf-section">${secLabel("pricing · hero")}
      <p class="eyebrow">Pricing</p>
      <h1 class="wf">Pricing that scales with your people.</h1>
      <p class="wf">Simple per-employee-per-month pricing. Every plan includes unlimited access — no surprise per-visit fees.</p>
      <div style="margin-top:10px;"><span class="toggle-pill"><span class="on">Per employee / mo</span><span>Annual (−15%)</span></span></div>
      ${S.dir === "C" ? annot("plans also reachable from the rail's $ tab") : ""}
    </div>
    <div class="wf-section tint">${secLabel("plans")}
      <div class="grid g3">
        ${plans
          .map(
            (pl) => `<div class="card plan ${pl.feat ? "feat" : ""}">
            ${pl.feat ? '<span class="chip" style="background:var(--accent);color:#fff;border-color:var(--ink);align-self:flex-start;">Most popular</span>' : ""}
            <h3 class="wf">${pl.n}</h3>
            <div class="price">${pl.p}<small> /emp/mo</small></div>
            <ul>${pl.items.map((i) => `<li>${i}</li>`).join("")}</ul>
            <span class="btn ${pl.feat ? "primary" : ""} sm" style="margin-top:8px;">Choose ${pl.n}</span>
          </div>`
          )
          .join("")}
      </div>
    </div>
    <div class="wf-section">${secLabel("comparison")}
      <h2 class="wf">Compare plans</h2>
      <table class="cmptable" style="margin-top:14px;">
        <thead><tr><th></th><th>Essential</th><th>Plus</th><th>Complete</th></tr></thead>
        <tbody>${rows
          .map(
            (r) => `<tr><td>${r[0]}</td><td class="c">${r[1]}</td><td class="c">${r[2]}</td><td class="c">${r[3]}</td></tr>`
          )
          .join("")}</tbody>
      </table>
    </div>
    <div class="wf-section">${secLabel("faq")}
      <h2 class="wf">Questions, answered</h2>
      <div class="faq" style="margin-top:8px;">${faqs.map((q) => `<div class="q">${q}</div>`).join("")}</div>
    </div>
    ${ctaBanner("Get a quote built around your headcount.")}
    ${footer()}`;
  }

  function pageBody() {
    if (S.page === "eap") return pageEAP();
    if (S.page === "pricing") return pagePricing();
    return pageHome();
  }

  // =====================================================
  //  COMPOSE FRAME PER DIRECTION
  // =====================================================
  const DIRS = {
    A: { name: "Editorial Mega-Menu", blurb: "Classic sticky header with three hover/click mega-menus. Patient vs. clinician lives in a dual Login dropdown — familiar, content-rich, zero friction to browse before committing." },
    B: { name: "Role-First Split Entry", blurb: "A persistent role bar asks \"who are you?\" before anything else. Nav labels, hero and CTAs all rewrite themselves around patient or clinician — opinionated and personal." },
    C: { name: "Slim Rail + Command", blurb: "App-like left rail for primary nav with a persistent role pill, plus a ⌘K command launcher. Modern, compact, and scales to a logged-in product feel." },
  };

  function render() {
    document.body.classList.toggle("dir-a", S.dir === "A");
    const url = `medflow.co/${S.page === "home" ? "" : S.page}`;
    let body;
    if (S.dir === "A") body = navA() + pageBody();
    else if (S.dir === "B") body = navB() + pageBody();
    else body = railC(pageBody());

    const d = DIRS[S.dir];
    document.getElementById("stage").innerHTML = `
      <div class="dir-caption">
        <div class="tag">${S.dir}</div>
        <div><h2>Direction ${S.dir} — ${d.name} ${roleChip()}</h2><p>${d.blurb}</p></div>
      </div>
      <div class="frame">
        <div class="frame-bar"><i></i><i></i><i></i><span class="url">🔒 ${url}</span></div>
        <div class="canvas">${body}</div>
      </div>`;
    syncControls();
  }

  // =====================================================
  //  INTERACTIONS (delegated)
  // =====================================================
  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-act]");
    if (!t) return;
    const act = t.dataset.act;
    const val = t.dataset.val;
    if (act === "role") { S.role = val; render(); }
    else if (act === "nav") { if (val === "more") return; S.page = val; render(); }
    else if (act === "login") {
      const pop = document.querySelector("[data-login]");
      if (pop) pop.classList.toggle("open");
      e.stopPropagation();
    } else if (act === "mega") {
      const open = document.querySelector(`[data-mega="${val}"]`);
      const wasOpen = open && open.classList.contains("open");
      document.querySelectorAll(".mega").forEach((m) => m.classList.remove("open"));
      if (open && !wasOpen) open.classList.add("open");
      e.stopPropagation();
    }
  });
  document.addEventListener("click", (e) => {
    if (!e.target.closest("[data-login]") && !e.target.closest('[data-act="login"]')) {
      const pop = document.querySelector("[data-login]");
      if (pop) pop.classList.remove("open");
    }
  });

  // control bar sync
  function syncControls() {
    document.querySelectorAll("[data-dir]").forEach((b) => b.classList.toggle("on", b.dataset.dir === S.dir));
    document.querySelectorAll("[data-page]").forEach((b) => b.classList.toggle("on", b.dataset.page === S.page));
  }

  // expose
  window.MFApp = {
    setDir: (d) => { S.dir = d; render(); },
    setPage: (p) => { S.page = p; render(); },
    render,
  };

  render();
})();
