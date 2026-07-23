/* ZAI 3D digital human.
 *
 * Renders a glTF avatar (Ready Player Me / PlayerZero / Avaturn / any GLB
 * carrying ARKit or Oculus viseme morph targets) and drives its face in real
 * time.
 *
 * Lip sync has two paths, chosen by what the voice layer can give us:
 *
 *   audio    When speech arrives as an audio buffer (Azure TTS), the signal is
 *            analysed through a Web Audio AnalyserNode and mapped to visemes.
 *            This is language-independent, so Arabic behaves exactly like
 *            English with no phoneme dictionary.
 *
 *   timeline When speech comes from the browser's own synthesiser, its audio
 *            cannot be tapped. A speech-cadence oscillator plus word-boundary
 *            emphasis is used instead. Less accurate, still convincing.
 *
 * Everything degrades: no WebGL, no model, or a load failure falls back to the
 * 2D presenter rather than showing an empty panel.
 */
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

/* ---------------- tunables ---------------- */

/* Whole-model yaw that cancels the baked idle clip's facing direction.
   The clip drives all bone animation including eyes, neck, and head —
   this only rotates the entire model so the shoulders face the camera. */
const BODY_YAW = 0.50;

/* Two rig families are supported.

   Oculus visemes (viseme_aa, viseme_O ...) are purpose-built mouth shapes: if
   present, they are used directly.

   ARKit rigs (jawOpen, mouthFunnel, mouthPucker ...) have no visemes at all —
   they are facial muscles. A viseme is therefore built as a RECIPE: a weighted
   blend of several ARKit shapes that together form that mouth position. */

const SLOTS = {
  jawOpen:      ['jawOpen', 'viseme_aa'],
  mouthClose:   ['mouthClose', 'viseme_sil'],
  mouthFunnel:  ['mouthFunnel', 'viseme_O'],
  mouthPucker:  ['mouthPucker', 'viseme_U'],
  mouthStretchL:['mouthStretch_L', 'mouthStretchLeft', 'viseme_I'],
  mouthStretchR:['mouthStretch_R', 'mouthStretchRight'],
  mouthPressL:  ['mouthPress_L', 'mouthPressLeft', 'viseme_PP'],
  mouthPressR:  ['mouthPress_R', 'mouthPressRight'],
  mouthLowerL:  ['mouthLowerDown_L', 'mouthLowerDownLeft'],
  mouthLowerR:  ['mouthLowerDown_R', 'mouthLowerDownRight'],
  blinkL:       ['eyeBlink_L', 'eyeBlinkLeft', 'eyesClosed'],
  blinkR:       ['eyeBlink_R', 'eyeBlinkRight'],
  browInner:    ['browInnerUp'],
  browOuterL:   ['browOuterUp_L', 'browOuterUpLeft'],
  browOuterR:   ['browOuterUp_R', 'browOuterUpRight'],
  smileL:       ['mouthSmile_L', 'mouthSmileLeft'],
  smileR:       ['mouthSmile_R', 'mouthSmileRight'],
};

/* Direct Oculus visemes, preferred when the rig has them. */
const OCULUS = ['viseme_sil', 'viseme_PP', 'viseme_FF', 'viseme_TH', 'viseme_DD',
  'viseme_kk', 'viseme_CH', 'viseme_SS', 'viseme_nn', 'viseme_RR',
  'viseme_aa', 'viseme_E', 'viseme_I', 'viseme_O', 'viseme_U'];

/* ARKit recipes, tuned so the progression from closed to wide reads clearly
   at panel size rather than being anatomically exact. */
const RECIPES = {
  sil: { mouthClose: 0.18 },
  PP:  { mouthClose: 0.55, mouthPressL: 0.45, mouthPressR: 0.45 },
  I:   { jawOpen: 0.16, mouthStretchL: 0.42, mouthStretchR: 0.42 },
  E:   { jawOpen: 0.30, mouthStretchL: 0.28, mouthStretchR: 0.28 },
  O:   { jawOpen: 0.42, mouthFunnel: 0.55 },
  U:   { jawOpen: 0.14, mouthPucker: 0.70 },
  aa:  { jawOpen: 0.80, mouthLowerL: 0.25, mouthLowerR: 0.25 },
};

/* Openness bands -> viseme. At 300px, the difference between a wide "aa" and a
   rounded "O" is what the eye actually registers. */
const BANDS = [
  [0.06, 'sil'], [0.16, 'PP'], [0.30, 'I'], [0.46, 'E'],
  [0.62, 'O'], [0.80, 'aa'], [1.01, 'aa'],
];

export class DigitalHuman {
  constructor(container) {
    this.container = container;
    this.slots = {};           // slot name -> [{mesh, index}]
    this.oculus = {};          // oculus viseme -> [{mesh, index}]
    this.current = {};         // viseme name -> current weight
    this.speaking = false;
    this.emphasis = 0;
    this.blinkAt = performance.now() + 3000;
    this.blinkPhase = 0;
    this.ready = false;

    this._onResize = () => this.resize();
  }

  static supported() {
    try {
      const c = document.createElement('canvas');
      return !!(window.WebGLRenderingContext &&
        (c.getContext('webgl2') || c.getContext('webgl')));
    } catch (_) { return false; }
  }

  async load(url, opts = {}) {
    const w = this.container.clientWidth || 300;
    const h = this.container.clientHeight || 400;

    this.scene = new THREE.Scene();
    // Long-lens portrait FOV. Anything wider makes the face look stretched.
    this.camera = new THREE.PerspectiveCamera(22, w / h, 0.1, 100);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    this.renderer.setClearColor(0x0d1a2c, 1);   // matches --navy stage background
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(w, h);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.domElement.className = 'avatar-media';
    this.container.appendChild(this.renderer.domElement);
    this.canvas = this.renderer.domElement;

    // Studio portrait lighting. Cool ambient with a neutral key and a stronger
    // cool rim on the opposite side is what reads as "corporate headshot"
    // rather than "game render". The rim separates the head from the
    // background, which is the single most important cue for perceived depth.
    this.scene.add(new THREE.HemisphereLight(0xf0f4ff, 0x162236, 0.75));

    const key = new THREE.DirectionalLight(0xfff5e8, 1.6);
    key.position.set(1.6, 2.4, 2.2);
    this.scene.add(key);

    const rim = new THREE.DirectionalLight(0xa8c6ff, 1.4);
    rim.position.set(-2.4, 1.6, -1.6);
    this.scene.add(rim);

    const fill = new THREE.DirectionalLight(0xffe8c8, 0.35);
    fill.position.set(-1.2, 0.4, 2.2);
    this.scene.add(fill);

    // Uncompressed glTF only. If a future model reports extensionsRequired
    // (run ops/check_avatar.py), the matching decoder must be vendored with
    // its original examples/jsm folder layout intact — the loaders import
    // their dependencies by relative path.
    const gltf = await new GLTFLoader().loadAsync(url);
    this.model = gltf.scene;
    this.scene.add(this.model);
    // Bone world positions are stale straight out of the loader. Without this
    // the head lookup returns the origin and the camera aims at nothing.
    this.model.updateMatrixWorld(true);

    // Baked idle animation. Avaturn exports one clip; if a future model
    // carries several, favour whichever contains "idle" in the name.
    if (gltf.animations && gltf.animations.length) {
      this.mixer = new THREE.AnimationMixer(this.model);
      const clip = gltf.animations.find((c) => /idle|neutral|stand/i.test(c.name))
                 || gltf.animations[0];
      this.mixer.clipAction(clip).play();
      console.info(`[3D] playing animation "${clip.name}"`);
    }

    this.indexMorphTargets();
    this.frameOnHead(opts.zoom ?? 1.0, opts.offsetY ?? 0);

    this.clock = new THREE.Clock();
    this.ready = true;
    this.animate();

    window.addEventListener('resize', this._onResize);
    return this;
  }

  /* Map every viseme name to the meshes and morph indices that carry it.
     Ready Player Me splits the face across Wolf3D_Head, _Teeth and _Beard, so
     a viseme usually drives several meshes at once. */
  indexMorphTargets() {
    this.slots = {};
    this.oculus = {};

    this.model.traverse((node) => {
      if (!node.isMesh || !node.morphTargetDictionary) return;
      node.frustumCulled = false;

      for (const name of OCULUS) {
        const idx = node.morphTargetDictionary[name];
        if (idx !== undefined) (this.oculus[name] ||= []).push({ mesh: node, index: idx });
      }
      for (const [slot, candidates] of Object.entries(SLOTS)) {
        for (const key of candidates) {
          const idx = node.morphTargetDictionary[key];
          if (idx === undefined) continue;
          (this.slots[slot] ||= []).push({ mesh: node, index: idx });
          break;
        }
      }
    });

    this.useOculus = Object.keys(this.oculus).length >= 8;
    const n = this.useOculus ? Object.keys(this.oculus).length
                             : Object.keys(this.slots).length;
    if (!n) {
      console.warn('[3D] model has no viseme or ARKit morph targets; '
                 + 'the mouth will not move');
    } else {
      console.info(`[3D] driving ${this.useOculus ? 'Oculus visemes' : 'ARKit shapes'} `
                 + `(${n} targets found)`);
    }
  }

  /* Frame the head rather than the whole body: this is a presenter panel, not
     a character viewer. Falls back to the model bounding box if no head bone. */
  frameOnHead(zoom, offsetY) {
    let head = null;
    this.model.traverse((n) => {
      if (!head && n.isBone && /^(mixamorig)?head$/i.test(n.name)) head = n;
    });
    if (!head) {
      this.model.traverse((n) => {
        if (!head && n.isBone && /head/i.test(n.name)) head = n;
      });
    }

    const box = new THREE.Box3().setFromObject(this.model);
    const target = new THREE.Vector3();

    if (head) {
      head.getWorldPosition(target);
      target.y += 0.04;
      console.info(`[3D] framing on bone "${head.name}"`);
    } else {
      // No head bone: aim near the top of the bounding box, where a head is.
      box.getCenter(target);
      target.y = box.max.y - (box.max.y - box.min.y) * 0.11;
      console.warn('[3D] no head bone found; framing on bounding box');
    }
    target.y += offsetY;

    const height = Math.max(0.01, box.max.y - box.min.y);
    console.info(`[3D] model height ${height.toFixed(2)}, `
               + `head at y=${target.y.toFixed(2)}`);

    // Head-and-shoulders portrait framing. The camera sits back far enough
    // that the face reads as a person on a call, not a passport photo. The
    // vertical offset drops the target so the eyeline lands in the upper
    // third of the frame — the composition every corporate portrait uses.
    const distance = (height * 0.9) / Math.max(0.2, zoom);
    this.camera.position.set(target.x, target.y - height * 0.045, target.z + distance);
    this.lookTarget = target;
    this.camera.lookAt(this.lookTarget);
  }

  resize() {
    if (!this.ready) return;
    const w = this.container.clientWidth || 300;
    const h = this.container.clientHeight || 400;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  /* ---------------- speech drive ---------------- */

  /* Route a playing HTMLAudioElement through an analyser. This is what makes
     Arabic work: the mouth follows the sound, not the spelling. */
  attachAudio(audioEl) {
    try {
      this.audioCtx ||= new (window.AudioContext || window.webkitAudioContext)();
      if (this.audioCtx.state === 'suspended') this.audioCtx.resume();
      const src = this.audioCtx.createMediaElementSource(audioEl);
      this.analyser = this.audioCtx.createAnalyser();
      this.analyser.fftSize = 1024;
      this.analyser.smoothingTimeConstant = 0.55;
      this.bins = new Uint8Array(this.analyser.frequencyBinCount);
      src.connect(this.analyser);
      this.analyser.connect(this.audioCtx.destination);
      this.driveMode = 'audio';
    } catch (err) {
      console.warn('[3D] audio analysis unavailable, using timeline', err);
      this.driveMode = 'timeline';
    }
  }

  /* ---------------- text-to-viseme (reactive) ----------------
     When no audio stream is available, the spoken TEXT drives the mouth.

     Pre-timeline approach failed because we don't know the TTS engine's
     speaking rate. This version works REACTIVELY: the text is parsed into
     words, each word into a viseme sequence. Each onboundary event (or
     backup timer) from the TTS engine advances to the next word. Phonemes
     within a word play at a fixed rate. Result: word transitions are paced
     by the engine, only intra-word timing is estimated. */

  /* Letter -> viseme. Covers Latin and Arabic. */
  static charToViseme(ch) {
    const c = ch.toLowerCase();
    if ('aàáâä'.includes(c))  return 'aa';
    if ('eèéêë'.includes(c))  return 'E';
    if ('iìíîï'.includes(c))  return 'I';
    if ('oòóôö'.includes(c))  return 'O';
    if ('uùúûü'.includes(c))  return 'U';
    if ('pbm'.includes(c))    return 'PP';
    if ('fv'.includes(c))     return 'FF';
    if ('dtln'.includes(c))   return 'DD';
    if ('kg'.includes(c))     return 'kk';
    if ('sz'.includes(c))     return 'SS';
    if ('r'.includes(c))      return 'RR';
    if ('jy'.includes(c))     return 'CH';
    if ('w'.includes(c))      return 'U';
    if ('h'.includes(c))      return 'aa';
    if ('cq'.includes(c))     return 'kk';
    if ('x'.includes(c))      return 'SS';
    if ('بپ'.includes(c))     return 'PP';
    if ('ف'.includes(c))      return 'FF';
    if ('ثذ'.includes(c))     return 'TH';
    if ('تدطضنل'.includes(c)) return 'DD';
    if ('كقگ'.includes(c))    return 'kk';
    if ('سصزژ'.includes(c))   return 'SS';
    if ('شجچ'.includes(c))    return 'CH';
    if ('ر'.includes(c))      return 'RR';
    if ('م'.includes(c))      return 'PP';
    if ('اآأإءعغحخه'.includes(c)) return 'aa';
    if ('و'.includes(c))      return 'O';
    if ('يئى'.includes(c))    return 'I';
    if ('َ'.includes(c))      return 'aa';
    if ('ُ'.includes(c))      return 'U';
    if ('ِ'.includes(c))      return 'I';
    return null;
  }

  /* Parse a single word into a viseme sequence, merging adjacent duplicates. */
  static wordToVisemes(word) {
    const seq = [];
    for (const ch of word) {
      const v = DigitalHuman.charToViseme(ch);
      if (!v) continue;
      if (seq.length && seq[seq.length - 1] === v) continue; // merge
      seq.push(v);
    }
    if (!seq.length) seq.push('aa'); // fallback for unknown scripts
    return seq;
  }

  /* Expand digits to approximate phonetic spellings so the viseme parser
     has letters to work with. Detects Arabic text automatically and uses
     Arabic number words so the mouth shapes match فاطمة, not Zira. */
  static expandNumbers(text) {
    // Detect language from the text itself.
    const arabicChars = (text.match(/[\u0600-\u06FF]/g) || []).length;
    const isArabic = arabicChars >= 2;

    const EN_DIGITS = ['zero','one','two','three','four','five','six','seven','eight','nine'];
    const EN_TEENS = ['ten','eleven','twelve','thirteen','fourteen','fifteen',
                      'sixteen','seventeen','eighteen','nineteen'];
    const EN_TENS = ['','','twenty','thirty','forty','fifty','sixty','seventy','eighty','ninety'];

    const AR_DIGITS = ['صفر','واحد','اثنان','ثلاثة','أربعة','خمسة','ستة','سبعة','ثمانية','تسعة'];
    const AR_TEENS = ['عشرة','أحد عشر','اثنا عشر','ثلاثة عشر','أربعة عشر','خمسة عشر',
                      'ستة عشر','سبعة عشر','ثمانية عشر','تسعة عشر'];
    const AR_TENS = ['','','عشرون','ثلاثون','أربعون','خمسون','ستون','سبعون','ثمانون','تسعون'];

    const DIGITS = isArabic ? AR_DIGITS : EN_DIGITS;
    const TEENS = isArabic ? AR_TEENS : EN_TEENS;
    const TENS = isArabic ? AR_TENS : EN_TENS;
    const HUNDRED = isArabic ? 'مائة' : 'hundred';
    const POINT = isArabic ? 'فاصلة' : 'point';

    return text.replace(/\d+(\.\d+)?/g, (m) => {
      if (m.includes('.')) {
        const [whole, frac] = m.split('.');
        const w = DIGITS[+whole] || whole;
        const f = [...frac].map(d => DIGITS[+d] || d).join(' ');
        return `${w} ${POINT} ${f}`;
      }
      const n = parseInt(m, 10);
      if (n < 10) return DIGITS[n];
      if (n < 20) return TEENS[n - 10];
      if (n < 100) {
        const t = TENS[Math.floor(n / 10)];
        const u = n % 10 ? ' ' + DIGITS[n % 10] : '';
        return isArabic ? (u.trim() + ' و' + t) : (t + u);
      }
      if (n < 1000) {
        const h = DIGITS[Math.floor(n / 100)] + ' ' + HUNDRED;
        const rem = n % 100;
        if (!rem) return h;
        const remStr = rem < 10 ? DIGITS[rem]
                     : rem < 20 ? TEENS[rem - 10]
                     : TENS[Math.floor(rem / 10)] + (rem % 10 ? ' ' + DIGITS[rem % 10] : '');
        return isArabic ? `${h} و${remStr}` : `${h} ${remStr}`;
      }
      return [...m].map(d => DIGITS[+d] || d).join(' ');
    });
  }

  /* Parse text into array of words, each with a viseme sequence.
     
     Numbers like "24" are ONE word in our list but the TTS speaks them as
     "twenty four" — TWO boundary events. Without tracking this, the extra
     boundary pushes wordIdx ahead and later words ("countries") never sync.
     Each word stores how many TTS boundaries it will consume. */
  parseWords(text) {
    const originalWords = text.split(/[\s]+/).filter(w => w.length > 0);
    return originalWords.map(w => {
      const expanded = DigitalHuman.expandNumbers(w);
      const expandedParts = expanded.split(/[\s]+/).filter(s => s.length > 0);
      const allVisemes = expandedParts.flatMap(s => DigitalHuman.wordToVisemes(s));
      return {
        text: w,
        visemes: allVisemes.length ? allVisemes : DigitalHuman.wordToVisemes(w),
        // "24" → "twenty four" → 2 boundaries to consume before advancing.
        ttsBoundaries: expandedParts.length,
      };
    });
  }

  startSpeaking(text) {
    this.speaking = true;
    this.t0 = performance.now();
    this.emphasis = 0;

    if (text && this.driveMode !== 'audio') {
      this._words = this.parseWords(text);
      this._wordIdx = 0;
      this._wordStartT = this.t0;
      this._phoneIdx = 0;
      this._gotBoundary = false;
      this._boundaryCount = 0;
      this._wordBoundariesLeft = this._words[0]?.ttsBoundaries || 1;
      this._lastBoundaryT = this.t0;
      console.info(`[3D] viseme words: ${this._words.length} words, `
                 + `${this._words.reduce((s, w) => s + w.visemes.length, 0)} phonemes`);
    } else {
      this._words = null;
    }
  }

  emphasise(source) {
    this.emphasis = 1;
    if (!this._words) return;

    const now = performance.now();

    if (source === 'tts') {
      this._gotBoundary = true;
      this._boundaryCount++;
      if (this._boundaryCount <= 1) {
        console.debug(`[3D] first boundary (word 0), skipping`);
        return;
      }

      // Consume one boundary for the current word.
      // Numbers produce multiple TTS boundaries ("24" → "twenty" + "four").
      // Don't advance to the next word until all boundaries are consumed.
      // BUT reset the viseme playback so the mouth keeps moving.
      this._wordBoundariesLeft--;
      if (this._wordBoundariesLeft > 0) {
        // Restart visemes from the midpoint — the TTS just started a new
        // sub-word ("four" after "twenty"), so the mouth should show new shapes.
        const word = this._words[this._wordIdx];
        const halfVisemes = Math.floor((word?.visemes.length || 0) / 2);
        this._wordStartT = now - halfVisemes * 80; // jump to second half of visemes
        console.debug(`[3D] boundary #${this._boundaryCount} consuming for "${word?.text}" (${this._wordBoundariesLeft} left)`);
        return;
      }

      const gap = now - this._lastBoundaryT;
      console.debug(`[3D] boundary #${this._boundaryCount} gap=${gap.toFixed(0)}ms → word ${this._wordIdx + 1}`);
    } else if (source === 'timer') {
      if ((now - this.t0) < 1500) return;
      if (this._gotBoundary) return;
    }

    this._lastBoundaryT = now;

    if (this._wordIdx < this._words.length - 1) {
      this._wordIdx++;
      this._wordStartT = now;
      this._phoneIdx = 0;
      this._wordBoundariesLeft = this._words[this._wordIdx]?.ttsBoundaries || 1;
    }
  }

  stopSpeaking() {
    this.speaking = false;
    this.emphasis = 0;
    this._words = null;
  }

  /* Current viseme. Fast transitions (80ms) so each word shows distinct
     consonant-vowel shapes. The hold keeps the last shape visible until
     the next boundary interrupts. */
  currentViseme(now) {
    if (!this._words || !this._words.length) return { name: 'sil', weight: 0 };

    const word = this._words[Math.min(this._wordIdx, this._words.length - 1)];
    const visemes = word.visemes;
    const elapsed = now - this._wordStartT;

    // 80ms per viseme — fast enough to show 3-4 distinct shapes per word.
    // Short words get interrupted by the next boundary (fine — that's natural).
    // Long words (numbers) play through their full sequence.
    const phoneMs = 80;

    const idx = Math.min(Math.floor(elapsed / phoneMs), visemes.length - 1);
    const p = Math.min(1, (elapsed - idx * phoneMs) / phoneMs);

    // Past all visemes: hold the last shape until next boundary.
    if (idx >= visemes.length - 1 && p >= 1) {
      return { name: visemes[visemes.length - 1], weight: 0.50 };
    }

    // Sharp attack, quick release — creates visible open/close rhythm
    // that reads as speech rather than smooth breathing.
    const weight = 0.45 + 0.50 * Math.sin(p * Math.PI);
    return { name: visemes[idx], weight };
  }

  /* Audio-driven openness — used only when attachAudio() has connected a
     real audio signal (Azure TTS path). */
  audioOpenness() {
    if (!this.analyser) return 0;
    this.analyser.getByteFrequencyData(this.bins);
    let sum = 0;
    const upto = Math.floor(this.bins.length * 0.28);
    for (let i = 2; i < upto; i++) sum += this.bins[i];
    return Math.min(1, (sum / (upto - 2)) / 78);
  }

  /* Compute the goal weight of every driven target, then ease toward it.
     Instant switching looks like chattering teeth. */
  applyViseme(name, weight) {
    const goals = {};

    if (this.useOculus) {
      for (const v of OCULUS) goals[v] = 0;
      const key = `viseme_${name}`;
      goals[this.oculus[key] ? key : 'viseme_sil'] = weight;
      this.ease(this.oculus, goals);
      return;
    }

    for (const slot of Object.keys(this.slots)) {
      if (slot === 'blinkL' || slot === 'blinkR') continue;
      goals[slot] = 0;
    }
    const recipe = RECIPES[name] || RECIPES.sil;
    for (const [slot, amount] of Object.entries(recipe)) {
      goals[slot] = Math.min(1, amount * (0.35 + weight * 0.85));
    }
    this.ease(this.slots, goals);
  }

  ease(table, goals) {
    for (const [key, goal] of Object.entries(goals)) {
      const targets = table[key];
      if (!targets) continue;
      const prev = this.current[key] ?? 0;
      // 0.55 reaches 90% in ~3 frames (~50ms). Fast enough that each
      // phoneme's shape is visible before the next one starts.
      const next = prev + (goal - prev) * 0.55;
      this.current[key] = next;
      for (const { mesh, index } of targets) mesh.morphTargetInfluences[index] = next;
    }
  }

  /* ---------------- frame loop ---------------- */

  animate() {
    requestAnimationFrame(() => this.animate());
    if (!this.ready) return;
    const now = performance.now();

    // The mixer drives the baked skeleton animation including eyes, neck, and
    // head. We do NOT override any bones — the clip handles gaze naturally.
    if (this.mixer) this.mixer.update(this.clock.getDelta());

    if (this.speaking) {
      if (this.driveMode === 'audio' && this.analyser) {
        // Real audio path: amplitude drives openness, bands pick viseme.
        const open = this.audioOpenness();
        const band = BANDS.find(([threshold]) => open < threshold) || BANDS[BANDS.length - 1];
        this.applyViseme(band[1], Math.min(1, open * 1.15));
        const brow = Math.min(0.55, open * 0.35 + this.emphasis * 0.4);
        this.ease(this.slots, { browInner: brow * 0.7,
                                browOuterL: brow * 0.25, browOuterR: brow * 0.25 });
      } else if (this._words) {
        // Text-driven reactive path: word index advanced by onboundary,
        // phonemes within each word play at a fixed rate.
        const shape = this.currentViseme(now);
        this.applyViseme(shape.name, shape.weight);
        const brow = Math.min(0.55, shape.weight * 0.30 + this.emphasis * 0.4);
        this.ease(this.slots, { browInner: brow * 0.7,
                                browOuterL: brow * 0.25, browOuterR: brow * 0.25 });
      } else {
        this.applyViseme('sil', 0.15);
        this.ease(this.slots, { browInner: 0, browOuterL: 0, browOuterR: 0 });
      }
      this.emphasis = Math.max(0, this.emphasis - 0.05);
    } else {
      this.applyViseme('sil', 0.12);
      // Brows relax back to neutral between turns.
      this.ease(this.slots, { browInner: 0, browOuterL: 0, browOuterR: 0 });
    }

    // Body pose. With a baked clip, only the counter-rotation is applied —
    // adding sway on top would fight the mixer. Without one, a near-still
    // sway stands in, since a perfectly rigid figure is its own uncanny cue.
    if (this.model) {
      if (this.mixer) {
        this.model.rotation.y = BODY_YAW;
      } else {
        const t = now / 1000;
        this.model.rotation.y = Math.sin(t * 0.18) * 0.022;
        this.model.rotation.x = Math.sin(t * 0.13) * 0.009;
        this.model.position.y = Math.sin(t * 0.3) * 0.002;
      }
    }

    this.updateBlink(now);
    this.renderer.render(this.scene, this.camera);
  }

  updateBlink(now) {
    const targets = [...(this.slots.blinkL || []), ...(this.slots.blinkR || [])];
    if (!targets.length) return;

    if (now > this.blinkAt) {
      this.blinkPhase = 1;
      // Slightly more frequent while speaking.
      const base = this.speaking ? 1800 : 2600;
      const jitter = this.speaking ? 2400 : 3800;
      this.blinkAt = now + base + Math.random() * jitter;
    }
    if (this.blinkPhase > 0) {
      this.blinkPhase = Math.max(0, this.blinkPhase - 0.16);
      const w = Math.sin(this.blinkPhase * Math.PI);
      for (const { mesh, index } of targets) mesh.morphTargetInfluences[index] = w;
    }
  }

  dispose() {
    this.ready = false;
    window.removeEventListener('resize', this._onResize);
    this.renderer?.dispose();
    this.canvas?.remove();
  }
}