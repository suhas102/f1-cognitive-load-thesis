const pptxgen = require("pptxgenjs");
const path = require("path");

const FIG = (name) => path.join(__dirname, "figures", name);

// ---------- Palette ----------
const C = {
  navy: "12141C",
  navy2: "1B1F2B",
  steel: "3D4B63",
  red: "E10600",
  white: "FFFFFF",
  offwhite: "F5F6F8",
  panel: "EEF0F3",
  textDark: "16181F",
  textMuted: "5B6270",
  green: "1F8A55",
  amber: "C77700",
};

const FONT_HEAD = "Calibri";
const FONT_BODY = "Calibri";

let pres = new pptxgen();
pres.defineLayout({ name: "WIDE", width: 13.333, height: 7.5 });
pres.layout = "WIDE";
const W = 13.333, H = 7.5;

function darkBg(slide) { slide.background = { color: C.navy }; }
function lightBg(slide) { slide.background = { color: C.white }; }

function footer(slide, num) {
  slide.addText("Inferring Cognitive Load in F1 Drivers", {
    x: 0.5, y: H - 0.42, w: 7, h: 0.3, fontFace: FONT_BODY, fontSize: 9, color: "9098A8", align: "left",
  });
  slide.addText(String(num), {
    x: W - 1.0, y: H - 0.42, w: 0.6, h: 0.3, fontFace: FONT_BODY, fontSize: 9, color: "9098A8", align: "right",
  });
}

function sectionTag(slide, text, dark) {
  slide.addShape(pres.ShapeType.roundRect, {
    x: 0.5, y: 0.42, w: 2.6, h: 0.36, rectRadius: 0.08,
    fill: { color: dark ? "23273A" : C.panel }, line: { type: "none" },
  });
  slide.addText(text.toUpperCase(), {
    x: 0.5, y: 0.42, w: 2.6, h: 0.36, fontFace: FONT_BODY, fontSize: 11, bold: true,
    color: C.red, align: "center", valign: "middle", charSpacing: 1,
  });
}

function titleBar(slide, title, dark, sub) {
  slide.addText(title, {
    x: 0.5, y: 0.82, w: W - 1.0, h: sub ? 0.7 : 0.9, fontFace: FONT_HEAD, fontSize: 28, bold: true,
    color: dark ? C.white : C.textDark, align: "left",
  });
  if (sub) {
    slide.addText(sub, {
      x: 0.5, y: 1.5, w: W - 1.0, h: 0.4, fontFace: FONT_BODY, fontSize: 14, italic: true,
      color: dark ? "AAB2C4" : C.textMuted, align: "left",
    });
  }
}

function statTile(slide, x, y, w, h, value, label, opts = {}) {
  const dark = opts.dark || false;
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: dark ? C.navy2 : C.panel }, line: { type: "none" },
  });
  slide.addText(value, {
    x: x + 0.1, y: y + 0.12, w: w - 0.2, h: h * 0.55, fontFace: FONT_HEAD, fontSize: opts.valueSize || 26, bold: true,
    color: opts.valueColor || C.red, align: "center", valign: "bottom",
  });
  slide.addText(label, {
    x: x + 0.1, y: y + h * 0.55, w: w - 0.2, h: h * 0.42, fontFace: FONT_BODY, fontSize: opts.labelSize || 11,
    color: dark ? "C7CCDA" : C.textMuted, align: "center", valign: "top",
  });
}

function card(slide, x, y, w, h, heading, body, opts = {}) {
  const dark = opts.dark || false;
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.09,
    fill: { color: dark ? C.navy2 : C.white }, line: { color: opts.borderColor || C.panel, width: 1 },
  });
  if (opts.accentBar !== false) {
    slide.addShape(pres.ShapeType.roundRect, {
      x: x + 0.18, y: y + 0.16, w: 0.32, h: 0.32, rectRadius: 0.16,
      fill: { color: opts.accentColor || C.red }, line: { type: "none" },
    });
  }
  slide.addText(heading, {
    x: x + (opts.accentBar !== false ? 0.62 : 0.2), y: y + 0.12, w: w - (opts.accentBar !== false ? 0.8 : 0.4), h: 0.42,
    fontFace: FONT_HEAD, fontSize: opts.headSize || 15, bold: true,
    color: dark ? C.white : C.textDark, align: "left", valign: "middle",
  });
  slide.addText(body, {
    x: x + 0.22, y: y + 0.58, w: w - 0.44, h: h - 0.7, fontFace: FONT_BODY, fontSize: opts.bodySize || 11.5,
    color: dark ? "C7CCDA" : C.textMuted, align: "left", valign: "top", lineSpacingMultiple: 1.15,
  });
}

function tableSimple(slide, x, y, w, rows, opts = {}) {
  const colW = opts.colW || null;
  slide.addTable(rows, {
    x, y, w,
    colW,
    fontFace: FONT_BODY,
    fontSize: opts.fontSize || 12,
    color: C.textDark,
    border: { type: "solid", color: "D8DBE2", pt: 0.75 },
    autoPage: false,
    valign: "middle",
    margin: [4, 8, 4, 8],
  });
}

// ================= SLIDE 1: TITLE =================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addShape(pres.ShapeType.rect, { x: 0, y: 5.85, w: W, h: 0.04, fill: { color: C.red }, line: { type: "none" } });
  s.addText("MSc THESIS DEFENCE", { x: 0.9, y: 1.55, w: 8, h: 0.4, fontFace: FONT_BODY, fontSize: 13, bold: true, color: C.red, charSpacing: 2 });
  s.addText("Inferring Cognitive Load and Decision-Making Under Pressure in Formula 1 Drivers", {
    x: 0.9, y: 2.0, w: 11.0, h: 1.9, fontFace: FONT_HEAD, fontSize: 34, bold: true, color: C.white, align: "left", valign: "top", lineSpacingMultiple: 1.05,
  });
  s.addText("A Telemetry-Based Behavioural Modelling Approach", {
    x: 0.9, y: 3.95, w: 10.5, h: 0.55, fontFace: FONT_BODY, fontSize: 18, italic: true, color: "AAB2C4",
  });
  s.addText([
    { text: "Suhas Suresh", options: { bold: true, color: C.white, fontSize: 14 } },
    { text: "   |   MSc Artificial Intelligence and Data Science", options: { color: "AAB2C4", fontSize: 14 } },
  ], { x: 0.9, y: 6.15, w: 11, h: 0.35 });
  s.addText("Keele University   |   CSC-44120   |   Supervisor: Dr Nadia Kanwal   |   September 2026", {
    x: 0.9, y: 6.55, w: 11, h: 0.35, fontFace: FONT_BODY, fontSize: 12, color: "8892A6",
  });
}

// ================= SLIDE 2: AGENDA =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Overview", false);
  titleBar(s, "Presentation Roadmap", false);
  const items = [
    ["01", "Motivation", "Why cognitive load in Formula 1 matters"],
    ["02", "The Research Gap", "Rigour vs. scale in existing measurement approaches"],
    ["03", "Theoretical Framework & Objectives", "Four frameworks, four hypotheses (H1–H4)"],
    ["04", "Methodology", "Data, proxies, confound control, model selection"],
    ["05", "Results", "H1–H4 findings with tables, charts and figures"],
    ["06", "Validation", "Leakage safeguards and baseline comparisons"],
    ["07", "Discussion, Limitations & Conclusion", "Interpretation, contribution, and future work"],
  ];
  const colW = (W - 1.0) / 2, rowH = 0.92, gapX = 0.2, gapY = 0.14;
  items.forEach((it, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.5 + col * (colW + gapX);
    const y = 2.05 + row * (rowH + gapY);
    s.addShape(pres.ShapeType.roundRect, { x, y, w: colW, h: rowH, rectRadius: 0.08, fill: { color: C.panel }, line: { type: "none" } });
    s.addText(it[0], { x: x + 0.15, y, w: 0.85, h: rowH, fontFace: FONT_HEAD, fontSize: 22, bold: true, color: C.red, align: "center", valign: "middle" });
    s.addText(it[1], { x: x + 1.05, y: y + 0.1, w: colW - 1.2, h: 0.38, fontFace: FONT_HEAD, fontSize: 13.5, bold: true, color: C.textDark, valign: "middle" });
    s.addText(it[2], { x: x + 1.05, y: y + 0.46, w: colW - 1.2, h: 0.4, fontFace: FONT_BODY, fontSize: 10.5, color: C.textMuted, valign: "top" });
  });
  footer(s, 2);
}

// ================= SLIDE 3: MOTIVATION =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Motivation", false);
  titleBar(s, "Why Formula 1?", false, "An extreme, understudied test of cognitive load under real competitive pressure");
  const tiles = [
    ["5–6g", "Sustained lateral & longitudinal loads for 90+ minutes"],
    [">50°C", "Typical cockpit temperature during a race"],
    ["74–82%", "of max heart rate sustained through a race"],
    ["~99%", "of max heart rate during the most demanding qualifying laps"],
  ];
  const tw = (W - 1.0 - 3 * 0.25) / 4;
  tiles.forEach((t, i) => statTile(s, 0.5 + i * (tw + 0.25), 2.35, tw, 1.55, t[0], t[1], { valueSize: 30 }));
  card(s, 0.5, 4.35, W - 1.0, 2.3, "Physical and cognitive demand are tightly coupled",
    "A Formula 1 driver is holding the car at the limit of traction while also reading where rivals are, executing team strategy over the radio, and working a steering wheel with more buttons than most cockpits — often all at once, within a single lap (Brown, Stanton and Revell, 2019). Because small differences in execution compound across a season instead of averaging out (Jenkins and Floyd, 2001), even a small, reliably measured behavioural difference between drivers can matter in practice. Despite that, driver cognitive workload is still fairly under-studied compared to fields like aviation or the military, where workload measurement is already a mature area.",
    { headSize: 16, bodySize: 12.5 });
  footer(s, 3);
}

// ================= SLIDE 4: RESEARCH GAP =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "The Problem", false);
  titleBar(s, "A Rigour-Versus-Scale Trade-Off", false);
  const colW = (W - 1.0 - 0.4) / 2;
  card(s, 0.5, 2.15, colW, 3.9, "Laboratory & simulator research",
    "EEG caps, eye-tracking rigs, cardiac electrodes — these genuinely do track cognitive load well (Palinko et al., 2010; Gabaude et al., 2012; Angkan et al., 2024).\n\nThe problem is you can't strap any of that onto a driver mid-Grand Prix. So the methods rigorous enough to actually validate a proxy end up stuck in small, lab-based samples.",
    { accentColor: C.steel, headSize: 15.5, bodySize: 12.5 });
  card(s, 0.5 + colW + 0.4, 2.15, colW, 3.9, "Data-science work on race telemetry",
    "This side works at a scale lab methods can't touch — for example, clustering sim-racing telemetry into elite vs. novice driving profiles (Hojaji et al., 2024).\n\nBut it tends to just assume the telemetry is measuring something meaningful, rather than checking. Behavioural structure gets pulled out with no real test of whether it holds together as a construct, or survives an obvious confound like tyre wear.",
    { accentColor: C.red, headSize: 15.5, bodySize: 12.5 });
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y: 6.25, w: W - 1.0, h: 0.72, rectRadius: 0.1, fill: { color: C.navy }, line: { type: "none" } });
  s.addText("This thesis tries to sit right at that trade-off — rigorous enough to actually defend, at a scale large enough to be worth defending.", {
    x: 0.7, y: 6.25, w: W - 1.4, h: 0.72, fontFace: FONT_BODY, fontSize: 13.5, italic: true, color: C.white, valign: "middle",
  });
  footer(s, 4);
}

// ================= SLIDE 5: AIM & CONTRIBUTION =================
{
  const s = pres.addSlide();
  darkBg(s);
  sectionTag(s, "Research Aim", true);
  titleBar(s, "Tested, Not Assumed", true);
  s.addText("If I had to sum up the whole approach in one line:", {
    x: 0.5, y: 2.0, w: W - 1.0, h: 0.4, fontFace: FONT_BODY, fontSize: 14, color: "C7CCDA",
  });
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y: 2.5, w: W - 1.0, h: 1.7, rectRadius: 0.1, fill: { color: C.navy2 }, line: { color: C.red, width: 1.5 } });
  s.addText("Instead of assuming telemetry proxies actually reflect cognitive load, I built the whole pipeline to let that assumption fail — and to say so honestly if it did.", {
    x: 0.85, y: 2.5, w: W - 1.7, h: 1.7, fontFace: FONT_HEAD, fontSize: 18, italic: true, color: C.white, valign: "middle",
  });
  const contribs = [
    "A confound-controlled, leakage-safe way of testing proxy validity honestly, instead of just assuming it",
    "Run at a scale — 61 races, 28 drivers, 3 seasons — that lab-based work has never really attempted",
    "Being upfront about which proxies actually held up under testing, and which didn't",
    "A working, queryable tool (H4) built on whatever evidence actually survived, not on wishful thinking",
  ];
  const cw = (W - 1.0 - 3 * 0.2) / 4;
  contribs.forEach((t, i) => {
    const x = 0.5 + i * (cw + 0.2);
    s.addShape(pres.ShapeType.roundRect, { x, y: 4.55, w: cw, h: 2.05, rectRadius: 0.08, fill: { color: C.navy2 }, line: { type: "none" } });
    s.addText(String(i + 1), { x: x + 0.12, y: 4.65, w: 0.6, h: 0.5, fontFace: FONT_HEAD, fontSize: 20, bold: true, color: C.red });
    s.addText(t, { x: x + 0.15, y: 5.1, w: cw - 0.3, h: 1.4, fontFace: FONT_BODY, fontSize: 11, color: "C7CCDA", valign: "top", lineSpacingMultiple: 1.15 });
  });
  footer(s, 5);
}

// ================= SLIDE 6: THEORETICAL FRAMEWORK =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Literature", false);
  titleBar(s, "Four Theoretical Frameworks", false, "Each generates a distinct, testable prediction about behaviour under load");
  const th = [
    ["Situational Awareness", "Endsley (1995)", "Under high workload, attention narrows onto whatever seems most urgent right now — so a driver's focus should lock onto a rival car or a braking marker during a wheel-to-wheel fight, at the expense of everything else."],
    ["Cognitive Load Theory", "Sweller (1988)", "Working memory can only hold so much. Once the total demand — intrinsic, extraneous, and germane load combined — outstrips what's available, control precision should start to slip."],
    ["Dual-Process Theory", "Kahneman (2011)", "Fast, automatic System 1 versus slow, effortful System 2. Interestingly, Beilock and Carr (2001) found that consciously monitoring yourself under pressure can actually tighten up a well-practised skill, not just wreck it."],
    ["Attentional Control Theory", "Eysenck et al. (2007)", "This one splits things into processing efficiency (how much it costs you) versus effectiveness (how accurate the output is) — the two don't have to move together under pressure, and often don't."],
  ];
  const cw = (W - 1.0 - 3 * 0.25) / 4;
  const cardY = 2.35, cardH = 4.1;
  th.forEach((t, i) => {
    const x = 0.5 + i * (cw + 0.25);
    s.addShape(pres.ShapeType.roundRect, {
      x, y: cardY, w: cw, h: cardH, rectRadius: 0.09,
      fill: { color: C.white }, line: { color: C.panel, width: 1 },
    });
    s.addShape(pres.ShapeType.roundRect, {
      x: x + 0.18, y: cardY + 0.16, w: 0.32, h: 0.32, rectRadius: 0.16,
      fill: { color: C.red }, line: { type: "none" },
    });
    s.addText(t[0], {
      x: x + 0.62, y: cardY + 0.1, w: cw - 0.8, h: 0.72, fontFace: FONT_HEAD, fontSize: 13.5, bold: true,
      color: C.textDark, align: "left", valign: "top", lineSpacingMultiple: 1.02,
    });
    s.addText(t[1], {
      x: x + 0.22, y: cardY + 0.86, w: cw - 0.44, h: 0.3, fontFace: FONT_BODY, fontSize: 10, italic: true, color: C.red,
    });
    s.addText(t[2], {
      x: x + 0.22, y: cardY + 1.22, w: cw - 0.44, h: cardH - 1.36, fontFace: FONT_BODY, fontSize: 10.8,
      color: C.textMuted, align: "left", valign: "top", lineSpacingMultiple: 1.15,
    });
  });
  footer(s, 6);
}

// ================= SLIDE 7: OBJECTIVES / HYPOTHESES =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Research Objectives", false);
  titleBar(s, "Four Hypotheses (H1–H4)", false);
  const hs = [
    ["H1", "Construct Validity", "The three proxies — throttle smoothness, braking consistency, sector-time variance — actually work as indicators of cognitive load, both on their own and combined into one construct."],
    ["H2", "Within-Stint Trajectory", "Each proxy shifts in a systematic way over the course of a stint, in line with what Cognitive Load Theory and attentional-narrowing models would predict."],
    ["H3", "Confound-Controlled Classification", "Behavioural signatures can tell high-pressure moments apart from ordinary driving — and that still holds for a driver the model has never seen before."],
    ["H4", "Applied Reporting Tool", "Whichever H3 model performs best can be turned into something queryable: an accurate, confound-aware load estimate for a given driver and race."],
  ];
  hs.forEach((h, i) => {
    const y = 2.05 + i * 1.18;
    s.addShape(pres.ShapeType.roundRect, { x: 0.5, y, w: W - 1.0, h: 1.05, rectRadius: 0.08, fill: { color: C.panel }, line: { type: "none" } });
    s.addShape(pres.ShapeType.roundRect, { x: 0.5, y, w: 1.15, h: 1.05, rectRadius: 0.08, fill: { color: C.navy }, line: { type: "none" } });
    s.addText(h[0], { x: 0.5, y, w: 1.15, h: 1.05, fontFace: FONT_HEAD, fontSize: 26, bold: true, color: C.white, align: "center", valign: "middle" });
    s.addText(h[1], { x: 1.85, y: y + 0.08, w: 3.1, h: 0.9, fontFace: FONT_HEAD, fontSize: 14, bold: true, color: C.textDark, valign: "middle" });
    s.addText(h[2], { x: 5.05, y: y + 0.08, w: W - 5.55, h: 0.9, fontFace: FONT_BODY, fontSize: 11.5, color: C.textMuted, valign: "middle", lineSpacingMultiple: 1.1 });
  });
  footer(s, 7);
}

// ================= SLIDE 8: DATA & SCALE =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Methodology", false);
  titleBar(s, "Data Source and Scale", false, "OpenF1 API — full publicly available 2023–2025 calendar, not a hand-picked sample");
  const tiles = [
    ["71", "race weekends attempted (2023–2025)"],
    ["61", "races retrieved (85.9%) — no manual fixes or fabrication"],
    ["65,763", "laps in the fully complete analytic sample"],
    ["28", "drivers"],
  ];
  const tw = (W - 1.0 - 3 * 0.25) / 4;
  tiles.forEach((t, i) => statTile(s, 0.5 + i * (tw + 0.25), 2.35, tw, 1.5, t[0], t[1], { valueSize: 30 }));
  card(s, 0.5, 4.2, (W - 1.0) * 0.52, 2.45, "Why exhaustive collection, not a hand-picked sample",
    "An earlier pilot version of this project just picked 3 races expected to be pressure-heavy (Singapore, Suzuka, São Paulo, 2023). I dropped that approach for this thesis: cherry-picking races that way risks biasing exactly the variables the study depends on, a bigger and messier sample gives the H3 classifier an honest shot at generalising, and the second literature gap I identified — testing at real competitive scale — pretty much demanded it.",
    { headSize: 14, bodySize: 11 });
  card(s, 0.5 + (W - 1.0) * 0.52 + 0.3, 4.2, (W - 1.0) * 0.48 - 0.3, 2.45, "10 races dropped — logged, never patched",
    "Every one of those exclusions was an automatic decision by the pipeline, each with its own logged reason — null merge keys, mismatched timestamp formats, one flat-out 404. None of them were fixed by hand or filled in with imputed values. I wanted every result traceable back to a real, unmodified data point.",
    { accentColor: C.steel, headSize: 14, bodySize: 11 });
  footer(s, 8);
}

// ================= SLIDE 9: THREE PROXIES =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Methodology", false);
  titleBar(s, "Three Behavioural Proxies", false, "Each grounded in a specific strand of the theoretical framework");
  const proxies = [
    ["Throttle Smoothness", "Negative SD of the throttle-rate signal (how fast throttle position changes) within a lap. The smoother and more consistent the application, the higher the score.", "Meant to capture Cognitive Load Theory directly: fine motor control tends to degrade as demand rises (Sweller, 1988)."],
    ["Braking Consistency", "Negative SD of where a driver starts braking, measured across all laps in a stint. A brake point that keeps drifting suggests attentional consistency is slipping.", "Grounded in Starcke and Brand's (2012) work on attentional consistency under load."],
    ["Sector-Time Variance", "Rolling variance of sector lap times over a trailing 5-lap window — essentially, how consistent pace is at any given point in a stint.", "Draws on Cognitive Load Theory and attentional-narrowing accounts (Endsley, 1995)."],
  ];
  const cw = (W - 1.0 - 2 * 0.3) / 3;
  proxies.forEach((p, i) => {
    const x = 0.5 + i * (cw + 0.3);
    card(s, x, 2.3, cw, 4.2, p[0], p[1], { headSize: 14.5, bodySize: 11.5 });
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.2, y: 5.55, w: cw - 0.4, h: 0.75, rectRadius: 0.07, fill: { color: C.navy }, line: { type: "none" } });
    s.addText(p[2], { x: x + 0.32, y: 5.55, w: cw - 0.64, h: 0.75, fontFace: FONT_BODY, fontSize: 9.8, italic: true, color: C.white, valign: "middle" });
  });
  footer(s, 9);
}

// ================= SLIDE 10: METHODOLOGY PIPELINE (FIGURE) =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Methodology", false);
  titleBar(s, "Overall Pipeline Architecture", false, "One shared feature-engineering layer feeding four independent, hypothesis-specific branches");
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y: 2.25, w: W - 1.0, h: 4.55, rectRadius: 0.08, fill: { color: C.white }, line: { color: C.panel, width: 1 } });
  s.addImage({ path: FIG("fig_3_1_pipeline.png"), x: 0.75, y: 2.45, w: W - 1.5, h: (W - 1.5) * (819 / 1979) });
  footer(s, 10);
}

// ================= SLIDE 11: CONFOUND CONTROL & LEAKAGE-SAFE DESIGN =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Methodology", false);
  titleBar(s, "Confound Control & Leakage-Safe Design", false);
  card(s, 0.5, 2.15, (W - 1.0) * 0.48, 4.35, "Confound control",
    "Tyre age (TyreLife) and tyre compound change braking points, throttle application and lap time on their own — nothing to do with cognitive state.\n\nSo every model relating a proxy or the high-pressure label to an outcome controlled for both, and that was applied consistently across the H2 trajectory regressions and the H3 classifiers.\n\nFuel load I couldn't control for — OpenF1 doesn't expose it at the resolution I'd have needed. I've called that out as a limitation rather than glossing over it.",
    { headSize: 15, bodySize: 11.5, accentColor: C.steel });
  card(s, 0.5 + (W - 1.0) * 0.48 + 0.4, 2.15, (W - 1.0) * 0.52 - 0.4, 4.35, "Leakage-safe evaluation",
    "Because the proxies partly reflect an individual driver's own baseline style, a random fold split risks a model just learning to recognise the driver rather than the pressure signal itself.\n\nSo I used GroupKFold cross-validation, grouped by driver, throughout: each of the 28 drivers contributed laps to exactly one held-out fold and never showed up in both the training and test side of the same split.",
    { headSize: 15, bodySize: 11.5 });
  footer(s, 11);
}

// ================= SLIDE 12: ALGORITHM SELECTION =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Methodology", false);
  titleBar(s, "Model Selection Rationale (H3)", false, "Three classifiers spanning a deliberate range of flexibility — compared, not pre-chosen");
  const rows = [
    [{ text: "Model", options: { bold: true, fill: { color: C.navy }, color: C.white } },
     { text: "Why included", options: { bold: true, fill: { color: C.navy }, color: C.white } }],
    ["Logistic Regression", "Interpretable coefficients; linear log-odds baseline"],
    ["Random Forest", "Captures non-linear and interaction effects without explicit specification"],
    ["XGBoost", "Most flexible; expected (and confirmed) best discriminative performance, interpretability addressed via SHAP"],
  ];
  tableSimple(s, 0.5, 2.2, (W - 1.0) * 0.55, rows, { fontSize: 13, colW: [(W - 1.0) * 0.55 * 0.35, (W - 1.0) * 0.55 * 0.65] });
  card(s, 0.5 + (W - 1.0) * 0.55 + 0.4, 2.2, (W - 1.0) * 0.45 - 0.4, 4.2, "Why not SVM or a neural network",
    "With only 3 proxies and 2 confound covariates as features, neither seemed worth the trade-off:\n\n• An SVM's kernel-induced decision boundaries didn't add much here, and offered no interpretability edge over the tree-based options.\n\n• A neural network's real strength is learning higher-order interactions from lots of weak inputs — not needed when the interactions of interest were already made explicit through proxy engineering.\n\nTree-based ensembles match or beat neural networks on tabular data this size anyway, while staying much easier to interpret.",
    { headSize: 14, bodySize: 11, accentColor: C.steel });
  footer(s, 12);
}

// ================= SLIDE 13: RESULTS - H1 CONSTRUCT VALIDITY (PCA) =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Results — H1", false);
  titleBar(s, "Construct Validity: No Single Dominant Factor", false, "Principal component analysis of the three standardised proxies (n = 65,763 laps)");
  s.addChart(pres.ChartType.bar, [{
    name: "Variance explained",
    labels: ["PC1", "PC2", "PC3"],
    values: [38.5, 32.8, 28.6],
  }], {
    x: 0.5, y: 2.15, w: 6.6, h: 4.15,
    chartColors: [C.red],
    showTitle: true, title: "Variance Explained by Component (%)", titleFontSize: 13, titleColor: C.textDark,
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: C.textDark, dataLabelFontSize: 11,
    dataLabelFormatCode: "0.0",
    catAxisLabelColor: C.textMuted, valAxisLabelColor: C.textMuted,
    valAxisTitle: "% variance", showValAxisTitle: true, valAxisTitleFontSize: 10,
    valGridLine: { color: "E4E6EB", size: 1 }, catGridLine: { style: "none" },
    showLegend: false, barGapWidthPct: 40,
  });
  card(s, 7.35, 2.15, W - 7.35 - 0.5, 1.85, "Cronbach's alpha = 0.096",
    "Well below what's normally considered acceptable internal consistency — the three proxies clearly aren't interchangeable indicators of one reliable construct.",
    { headSize: 15, bodySize: 11.5 });
  card(s, 7.35, 4.15, W - 7.35 - 0.5, 2.15, "A near-even 3-way variance split",
    "38.5% / 32.8% / 28.6% across the first three components — not what you'd expect if the proxies were indexing one underlying cognitive-load construct. PC1 loaded positively on sector-time variance and braking consistency, but negatively on throttle smoothness.",
    { headSize: 15, bodySize: 11.5, accentColor: C.steel });
  footer(s, 13);
}

// ================= SLIDE 14: RESULTS - H1 KNOWN-GROUPS EFFECT SIZES =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Results — H1", false);
  titleBar(s, "Each Proxy Individually Validated — But Unevenly", false, "Known-groups comparison: high-pressure vs. baseline laps (Mann-Whitney U, BH-corrected)");
  s.addChart(pres.ChartType.bar, [{
    name: "Rank-biserial r",
    labels: ["Throttle\nsmoothness", "Braking\nconsistency", "Sector-time\nvariance"],
    values: [0.078, -0.060, 0.435],
  }], {
    x: 0.5, y: 2.15, w: 7.3, h: 4.15,
    chartColors: [C.red],
    showTitle: true, title: "Effect Size (rank-biserial r)", titleFontSize: 13, titleColor: C.textDark,
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: C.textDark, dataLabelFontSize: 11,
    dataLabelFormatCode: "0.000",
    catAxisLabelColor: C.textMuted, valAxisLabelColor: C.textMuted, catAxisLabelFontSize: 10.5,
    valGridLine: { color: "E4E6EB", size: 1 }, catGridLine: { style: "none" },
    showLegend: false, barGapWidthPct: 40,
  });
  card(s, 8.05, 2.15, W - 8.05 - 0.5, 4.15, "All significant, but wildly different sizes",
    "All three differences held up after Benjamini-Hochberg correction — but they don't tell the same story.\n\nThrottle smoothness and braking consistency: barely any separation at all (r = 0.078, −0.060).\n\nSector-time variance: a moderate effect (r = 0.435), with high-pressure laps sitting at a noticeably higher median.\n\nConfound-controlled mixed-effects models (Table 4.4) backed up all three effects under a stricter specification.",
    { headSize: 14.5, bodySize: 11 });
  footer(s, 14);
}

// ================= SLIDE 15: RESULTS - H2 WITHIN-STINT TRAJECTORY =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Results — H2", false);
  titleBar(s, "Within-Stint Trajectory: Confound-Controlled Decline", false, "Linear mixed-effects models, driver random intercept, 61 races / 28 drivers");
  const rows = [
    [{ text: "Proxy", options: { bold: true, fill: { color: C.navy }, color: C.white } },
     { text: "Raw lap–coeff.", options: { bold: true, fill: { color: C.navy }, color: C.white } },
     { text: "Raw p", options: { bold: true, fill: { color: C.navy }, color: C.white } },
     { text: "Confound-controlled p (BH)", options: { bold: true, fill: { color: C.navy }, color: C.white } }],
    ["Throttle smoothness", "−0.0051", ".011", ".005"],
    ["Braking consistency", "−0.126", "< .001", "< .001"],
    ["Sector-time variance", "−0.259", "< .001", ".007"],
  ];
  tableSimple(s, 0.5, 2.3, W - 1.0, rows, { fontSize: 14 });
  card(s, 0.5, 4.55, W - 1.0, 1.95, "All three proxies declined over a stint — even after adjustment",
    "The within-stint lap-count effect stayed significant for all three proxies even after adding TyreLife and Compound as covariates and applying Benjamini-Hochberg correction. So the decline can't just be tyre wear or a driver's stable personal style showing through — it's consistent with the kind of cumulative cognitive-load erosion H2 predicted.",
    { headSize: 14.5, bodySize: 12 });
  footer(s, 15);
}

// ================= SLIDE 16: RESULTS - H3 CLASSIFICATION PERFORMANCE =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Results — H3", false);
  titleBar(s, "Confound-Controlled Classification of High-Pressure Laps", false, "Driver-grouped 5-fold cross-validation — 23.2% positive (high-pressure) rate");
  s.addChart(pres.ChartType.bar, [
    { name: "Accuracy", labels: ["Naïve baseline", "Logistic Reg.", "Random Forest", "XGBoost"], values: [0.768, 0.766, 0.667, 0.677] },
    { name: "ROC-AUC", labels: ["Naïve baseline", "Logistic Reg.", "Random Forest", "XGBoost"], values: [0.500, 0.610, 0.736, 0.740] },
    { name: "F1", labels: ["Naïve baseline", "Logistic Reg.", "Random Forest", "XGBoost"], values: [0.000, 0.023, 0.492, 0.494] },
  ], {
    x: 0.5, y: 2.15, w: W - 1.0, h: 4.2, barDir: "col",
    chartColors: [C.steel, "9AA5B8", C.red],
    showTitle: false,
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: C.textDark, dataLabelFontSize: 9.5,
    dataLabelFormatCode: "0.000",
    catAxisLabelColor: C.textMuted, valAxisLabelColor: C.textMuted,
    valGridLine: { color: "E4E6EB", size: 1 }, catGridLine: { style: "none" },
    showLegend: true, legendPos: "b", legendColor: C.textMuted, legendFontSize: 11,
    barGapWidthPct: 30,
  });
  footer(s, 16);
}

// ================= SLIDE 17: RESULTS - H3 SHAP CONVERGENCE =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Results — H3", false);
  titleBar(s, "Sector-Time Variance Dominates — Three Independent Methods Agree", false);
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y: 2.2, w: 7.7, h: 4.3, rectRadius: 0.08, fill: { color: C.white }, line: { color: C.panel, width: 1 } });
  s.addImage({ path: FIG("fig_4_1_shap_summary.png"), x: 0.75, y: 2.55, w: 7.2, h: 7.2 * (310 / 1090) });
  s.addText("Figure 4.1 — SHAP summary plot, XGBoost classifier", { x: 0.75, y: 5.7, w: 7.2, h: 0.3, fontFace: FONT_BODY, fontSize: 10, italic: true, color: C.textMuted });
  card(s, 8.4, 2.2, W - 8.4 - 0.5, 4.3, "Three methods agree — this isn't a fluke",
    "Logistic coefficients, random forest importances, and SHAP values (mean |SHAP| = 0.764 vs. 0.171 and 0.080) all point the same way: sector-time variance dominates the high-pressure prediction.\n\nGetting the same answer from one linear method, one impurity-based method, and one game-theoretic (Shapley-value) method is a much stronger signal than any single model could give — it suggests the dominance is a real property of the data, not just an artefact of how one particular model happens to work.",
    { headSize: 14, bodySize: 11 });
  footer(s, 17);
}

// ================= SLIDE 18: RESULTS - H4 APPLIED TOOL =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Results — H4", false);
  titleBar(s, "From Model to Instrument: The Applied Reporting Tool", false, "1,171 queryable (race, driver) combinations across 61 races and 28 drivers");
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y: 2.2, w: 6.6, h: 3.9, rectRadius: 0.08, fill: { color: C.white }, line: { color: C.panel, width: 1 } });
  s.addImage({ path: FIG("fig_3_4_h4_app_live.png"), x: 1.6, y: 2.35, w: 4.4, h: 4.4 * (732 / 895) });
  const rows = [
    [{ text: "Field", options: { bold: true, fill: { color: C.navy }, color: C.white, fontSize: 10.5 } },
     { text: "Value", options: { bold: true, fill: { color: C.navy }, color: C.white, fontSize: 10.5 } }],
    ["Laps analysed", "77"],
    ["Mean predicted load probability", "0.428"],
    ["Field mean (same race)", "0.448 (−0.020)"],
    ["Laps flagged high-load", "32.5% (25 laps)"],
    ["Model", "XGBoost (ROC-AUC 0.740)"],
  ];
  tableSimple(s, 7.35, 2.2, W - 7.35 - 0.5, rows, { fontSize: 10.5 });
  card(s, 7.35, 5.55, W - 7.35 - 0.5, 1.55, "Live example: driver HAM, monaco_2025",
    "Screenshot of the actual desktop app run on this query. Predicted load already accounts for tyre compound and age (mean tyre age at sample: 14.7 laps, HARD/MEDIUM) via the shared confound-controlled pipeline.", { headSize: 12, bodySize: 9.8, accentBar: false });
  footer(s, 18);
}

// ================= SLIDE 19: VALIDATION =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Validation", false);
  titleBar(s, "Validation and Testing", false);
  const colW = (W - 1.0 - 0.4) / 2;
  card(s, 0.5, 2.15, colW, 2.0, "The leakage safeguard actually held up",
    "ROC-AUC standard deviation across the 5 driver-held-out folds came out at 0.007 (LogReg), 0.013 (RF), 0.013 (XGBoost). Spreads that narrow mean the results didn't depend much on which drivers happened to land in the held-out fold.",
    { headSize: 14, bodySize: 11 });
  card(s, 0.5 + colW + 0.4, 2.15, colW, 2.0, "It beats a naïve majority-class baseline",
    "Always predicting \"baseline\" gets you 0.768 accuracy / 0.500 ROC-AUC / 0.000 F1. RF and XGBoost give up a little accuracy but gain substantially on ROC-AUC and F1 — a sign they're genuinely picking something up from the proxies, not just guessing well.",
    { headSize: 14, bodySize: 11, accentColor: C.steel });
  card(s, 0.5, 4.35, colW, 2.3, "Keeping multiple comparisons honest",
    "I applied Benjamini-Hochberg correction within every family of repeated tests: the three known-groups comparisons (Table 4.3), the three confound-controlled high-pressure tests (Table 4.4), and the three within-stint slope tests (Table 4.5).",
    { headSize: 14, bodySize: 11 });
  card(s, 0.5 + colW + 0.4, 4.35, colW, 2.3, "H4 tested on both good and bad input",
    "I ran the batch CSV interface with driver-code, case-insensitive, and location-based queries, plus a deliberately invalid driver code — which just populated an error field for that one row instead of taking down the whole batch.",
    { headSize: 14, bodySize: 11, accentColor: C.steel });
  footer(s, 19);
}

// ================= SLIDE 20: DISCUSSION =================
{
  const s = pres.addSlide();
  darkBg(s);
  sectionTag(s, "Discussion", true);
  titleBar(s, "A Dissociation, Not a Contradiction", true, "Interpreted through Attentional Control Theory's efficiency–effectiveness distinction");
  const colW = (W - 1.0 - 0.5) / 2;
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y: 2.3, w: colW, h: 3.1, rectRadius: 0.09, fill: { color: C.navy2 }, line: { color: "3D4B63", width: 1 } });
  s.addText("Processing Efficiency", { x: 0.75, y: 2.5, w: colW - 0.5, h: 0.4, fontFace: FONT_HEAD, fontSize: 15, bold: true, color: "9AA5B8" });
  s.addText("Throttle smoothness & braking consistency", { x: 0.75, y: 2.92, w: colW - 0.5, h: 0.35, fontFace: FONT_BODY, fontSize: 11.5, italic: true, color: "C7CCDA" });
  s.addText("Barely any effect size at all (r = 0.078, −0.060). Drivers seem to hold onto accurate control by just throwing disproportionate effort at it — the cost gets paid quietly, out of view.", { x: 0.75, y: 3.35, w: colW - 0.5, h: 1.9, fontFace: FONT_BODY, fontSize: 12.5, color: "C7CCDA", lineSpacingMultiple: 1.2 });
  s.addShape(pres.ShapeType.roundRect, { x: 0.5 + colW + 0.5, y: 2.3, w: colW, h: 3.1, rectRadius: 0.09, fill: { color: C.navy2 }, line: { color: C.red, width: 1.5 } });
  s.addText("Processing Effectiveness", { x: 0.75 + colW + 0.5, y: 2.5, w: colW - 0.5, h: 0.4, fontFace: FONT_HEAD, fontSize: 15, bold: true, color: C.red });
  s.addText("Sector-time variance", { x: 0.75 + colW + 0.5, y: 2.92, w: colW - 0.5, h: 0.35, fontFace: FONT_BODY, fontSize: 11.5, italic: true, color: "C7CCDA" });
  s.addText("A moderate effect size (r = 0.435), and dominant across all three interpretation methods. Once demand outstrips capacity, the output itself starts to degrade.", { x: 0.75 + colW + 0.5, y: 3.35, w: colW - 0.5, h: 1.9, fontFace: FONT_BODY, fontSize: 12.5, color: "C7CCDA", lineSpacingMultiple: 1.2 });
  s.addText("Actually testing construct validity, rather than assuming it, changed the conclusions I would otherwise have drawn: a single composite score would have quietly hidden three proxies behaving in theoretically distinct ways.", {
    x: 0.5, y: 5.7, w: W - 1.0, h: 1.1, fontFace: FONT_BODY, fontSize: 13.5, italic: true, color: C.white, align: "center", valign: "middle",
  });
  footer(s, 20);
}

// ================= SLIDE 21: LIMITATIONS =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Limitations", false);
  titleBar(s, "What This Thesis Does Not Claim", false);
  const lims = [
    ["Fuel load stayed uncontrolled", "OpenF1 doesn't expose fuel load at the resolution I'd have needed. So the reported effects are net of tyre-related confounds only — not every confound someone could reasonably raise."],
    ["One category, three seasons", "I didn't test whether this generalises to other racing formats or regulation eras."],
    ["H4's generalisation is bounded", "Every driver/race you can query already sat inside the 61-race training pool. That's a correctness guarantee for the existing dataset — it isn't evidence the tool would perform well on a circuit it's never seen."],
    ["H4's usability wasn't tested on real users", "I tested the underlying software logic, not whether an actual non-technical coach or engineer would find the tool usable — that would need a proper user study."],
  ];
  const cw = (W - 1.0 - 0.3) / 2;
  lims.forEach((l, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.5 + col * (cw + 0.3);
    const y = 2.2 + row * 2.35;
    card(s, x, y, cw, 2.15, l[0], l[1], { headSize: 13.5, bodySize: 11, accentColor: C.amber });
  });
  footer(s, 21);
}

// ================= SLIDE 22: CONCLUSION =================
{
  const s = pres.addSlide();
  darkBg(s);
  sectionTag(s, "Conclusion", true);
  titleBar(s, "What This Thesis Established", true);
  const rows = [
    ["H1", "Not supported as a unified construct (α = 0.096); each proxy individually significant"],
    ["H2", "Supported — all three proxies declined significantly across a stint"],
    ["H3", "Supported — XGBoost distinguished high-pressure laps, ROC-AUC ≈ 0.740"],
    ["H4", "Supported — working, tested reporting tool built on the validated signal"],
  ];
  rows.forEach((r, i) => {
    const y = 2.15 + i * 0.85;
    s.addShape(pres.ShapeType.roundRect, { x: 0.5, y, w: 1.1, h: 0.72, rectRadius: 0.07, fill: { color: C.red }, line: { type: "none" } });
    s.addText(r[0], { x: 0.5, y, w: 1.1, h: 0.72, fontFace: FONT_HEAD, fontSize: 16, bold: true, color: C.white, align: "center", valign: "middle" });
    s.addShape(pres.ShapeType.roundRect, { x: 1.75, y, w: W - 2.25, h: 0.72, rectRadius: 0.07, fill: { color: C.navy2 }, line: { type: "none" } });
    s.addText(r[1], { x: 1.95, y, w: W - 2.65, h: 0.72, fontFace: FONT_BODY, fontSize: 12.5, color: "C7CCDA", valign: "middle" });
  });
  s.addShape(pres.ShapeType.roundRect, { x: 0.5, y: 5.75, w: W - 1.0, h: 1.15, rectRadius: 0.09, fill: { color: C.navy2 }, line: { color: C.red, width: 1.5 } });
  s.addText("The central contribution isn't a claim that telemetry fully captures cognitive load. It's a confound-controlled, leakage-safe way of testing that claim honestly, at a scale existing lab-based work simply can't reach.", {
    x: 0.75, y: 5.75, w: W - 1.5, h: 1.15, fontFace: FONT_BODY, fontSize: 13, italic: true, color: C.white, valign: "middle",
  });
  footer(s, 22);
}

// ================= SLIDE 23: FUTURE WORK =================
{
  const s = pres.addSlide();
  lightBg(s);
  sectionTag(s, "Future Work", false);
  titleBar(s, "Three Directions for Extension", false);
  const fw = [
    ["Additional Proxies", "Steering-input variability or gear-shift timing, run through the same pipeline, to see whether they turn out to be further distinguishable signals or just converge with sector-time variance."],
    ["Fuel Load as a Covariate", "Once fuel load is available at a fine enough resolution, adding it would close the one confound this thesis couldn't control for."],
    ["Neurophysiological Validation", "Pairing this pipeline with EEG or eye-tracking from practice or simulator sessions would let the telemetry proxies be checked against a direct measure of cognitive state — which is really the rigour-vs-scale trade-off this whole thesis was trying to work around."],
  ];
  const cw = (W - 1.0 - 2 * 0.3) / 3;
  fw.forEach((f, i) => {
    const x = 0.5 + i * (cw + 0.3);
    card(s, x, 2.3, cw, 4.2, f[0], f[1], { headSize: 14.5, bodySize: 12 });
    s.addText(String(i + 1), { x: x + cw - 0.65, y: 2.42, w: 0.45, h: 0.45, fontFace: FONT_HEAD, fontSize: 16, bold: true, color: C.red, align: "right" });
  });
  footer(s, 23);
}

// ================= SLIDE 24: THANK YOU =================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addShape(pres.ShapeType.rect, { x: 0, y: 5.85, w: W, h: 0.04, fill: { color: C.red }, line: { type: "none" } });
  s.addText("Thank You", { x: 0.9, y: 2.6, w: 11, h: 1.0, fontFace: FONT_HEAD, fontSize: 40, bold: true, color: C.white });
  s.addText("Questions & Discussion", { x: 0.9, y: 3.55, w: 11, h: 0.5, fontFace: FONT_BODY, fontSize: 18, italic: true, color: "AAB2C4" });
  s.addText("Suhas Suresh   |   suhassuresh1212@gmail.com", { x: 0.9, y: 6.15, w: 11, h: 0.35, fontFace: FONT_BODY, fontSize: 13, color: C.white });
  s.addText("MSc Artificial Intelligence and Data Science  —  Keele University  —  Supervisor: Dr Nadia Kanwal", { x: 0.9, y: 6.55, w: 11, h: 0.35, fontFace: FONT_BODY, fontSize: 11.5, color: "8892A6" });
}

pres.writeFile({ fileName: path.join(__dirname, "..", "ThesisPresentation.pptx") }).then((fn) => {
  console.log("Wrote:", fn);
}).catch((e) => { console.error(e); process.exit(1); });
