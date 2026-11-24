<script setup lang="ts">
/**
 * The hero landscape: a low-poly mountain range above a lake that mirrors it,
 * drawn with plain WebGL (no library).
 *
 * Map pins drop in along a trail to the summit (places visited, in green),
 * and a dashed route runs on to the next peak (places planned, in blue),
 * the same colors the app's map uses. A small airliner crosses the sky on a
 * dashed flight path. The trail starts from a lakeside town with a hotel
 * and a dock, and a tent is pitched beside it further along.
 *
 * Light theme is golden hour, with a low sun and drifting cloud. Dark theme is
 * night, with stars and an aurora. The camera drifts slowly and leans a little
 * toward the pointer. It pauses off screen and holds still for visitors who
 * prefer reduced motion. Without WebGL, the CSS sky behind the canvas shows.
 */
import { onBeforeUnmount, onMounted, ref } from "vue";

const canvas = ref<HTMLCanvasElement | null>(null);
let dispose = () => {};

const WATER = 0.07;

type Palette = {
  low: number[];
  rock: number[];
  snow: number[];
  tree: number[];
  fog: number[];
  light: number[];
  skyAmbient: number[];
  ground: number[];
  water: number[];
  sun: number[];
};

const PALETTES: Record<"light" | "dark", Palette> = {
  light: {
    low: [0.3, 0.44, 0.3],
    rock: [0.52, 0.47, 0.42],
    snow: [1.0, 0.97, 0.93],
    tree: [0.13, 0.3, 0.22],
    fog: [0.95, 0.86, 0.75],
    light: [1.15, 0.92, 0.7],
    skyAmbient: [0.5, 0.6, 0.72],
    ground: [0.34, 0.3, 0.26],
    water: [0.33, 0.52, 0.62],
    sun: [0.74, 0.42, 0.52],
  },
  dark: {
    low: [0.05, 0.12, 0.1],
    rock: [0.13, 0.17, 0.19],
    snow: [0.6, 0.72, 0.8],
    tree: [0.02, 0.07, 0.06],
    fog: [0.04, 0.085, 0.085],
    light: [0.45, 0.62, 0.8],
    skyAmbient: [0.14, 0.3, 0.3],
    ground: [0.03, 0.05, 0.05],
    water: [0.03, 0.1, 0.11],
    sun: [-0.5, 0.6, 0.62],
  },
};

const NOISE = `
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
             mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
  float s = 0.0, a = 0.5;
  for (int i = 0; i < 4; i++) { s += noise(p) * a; p *= 2.03; a *= 0.5; }
  return s;
}`;

const SKY_VERT = `
attribute vec2 aCorner;
varying vec2 vUv;
void main() { vUv = aCorner * 0.5 + 0.5; gl_Position = vec4(aCorner, 0.9999, 1.0); }`;

const SKY_FRAG = `
precision mediump float;
varying vec2 vUv;
uniform float uTime, uDark, uAspect, uWide;
uniform vec2 uSunAt;
${NOISE}
void main() {
  vec2 uv = vUv;
  vec2 p = vec2(uv.x * uAspect, uv.y);
  vec3 col;
  if (uDark < 0.5) {
    vec3 horizon = vec3(0.99, 0.84, 0.66), mid = vec3(0.86, 0.89, 0.88), zenith = vec3(0.56, 0.76, 0.92);
    col = mix(horizon, mid, smoothstep(0.28, 0.58, uv.y));
    col = mix(col, zenith, smoothstep(0.5, 1.0, uv.y));
    float d = distance(p, vec2(uSunAt.x * uAspect, uSunAt.y));
    col += vec3(1.0, 0.78, 0.5) * exp(-d * 4.5) * 0.6;
    col = mix(col, vec3(1.0, 0.97, 0.88), smoothstep(0.05, 0.038, d));
    float c = fbm(vec2(p.x * 1.5 + uTime * 0.012, uv.y * 5.5));
    c = smoothstep(0.5, 0.78, c) * smoothstep(0.4, 0.62, uv.y) * smoothstep(1.02, 0.8, uv.y);
    col = mix(col, vec3(1.0, 0.95, 0.88), c * 0.6);
  } else {
    col = mix(vec3(0.05, 0.11, 0.11), vec3(0.016, 0.03, 0.065), smoothstep(0.2, 0.9, uv.y));
    vec2 g = p * 85.0;
    float h = hash(floor(g));
    float star = step(0.986, h) * smoothstep(0.16, 0.0, length(fract(g) - 0.5));
    col += star * (0.55 + 0.45 * sin(uTime * 1.4 + h * 40.0)) * smoothstep(0.3, 0.6, uv.y);
    // Keep the aurora off the headline on wide layouts.
    float side = mix(1.0, smoothstep(0.2, 0.62, uv.x), uWide);
    for (int i = 0; i < 2; i++) {
      float fi = float(i);
      float x = p.x * (1.1 + fi * 0.5) + fi * 3.0;
      float wave = fbm(vec2(x * 0.8 + uTime * 0.02, fi * 5.0 + uTime * 0.015));
      float dy = uv.y - (0.56 + fi * 0.1 + (wave - 0.5) * 0.36);
      float band = dy > 0.0 ? exp(-dy * 6.0) : exp(dy * 38.0);
      float rays = 0.5 + 0.5 * noise(vec2(x * 16.0 + uTime * 0.07, fi));
      vec3 hue = mix(vec3(0.2, 1.0, 0.62), vec3(0.5, 0.32, 1.0), smoothstep(0.0, 0.32, dy));
      col += hue * band * rays * (0.42 - fi * 0.12) * smoothstep(0.12, 0.55, wave + 0.2) * side;
    }
    float md = distance(p, vec2(0.9 * uAspect, 0.86));
    col += vec3(0.75, 0.82, 0.95) * (smoothstep(0.028, 0.022, md) + exp(-md * 14.0) * 0.25);
  }
  gl_FragColor = vec4(col, 1.0);
}`;

const LAND_VERT = `
attribute vec3 aPos;
attribute vec3 aNormal;
attribute float aKind;
uniform mat4 uMvp;
uniform float uShift;
// Shared with the fragment shader, so the precision must match.
uniform mediump float uMirror, uWater;
varying vec3 vNormal;
varying float vHeight, vDepth, vKind;
void main() {
  vec3 pos = aPos;
  if (uMirror > 0.5) pos.y = 2.0 * uWater - pos.y;
  vec4 p = uMvp * vec4(pos, 1.0);
  p.x += uShift * p.w;
  gl_Position = p;
  vNormal = aNormal;
  vHeight = aPos.y;
  vDepth = p.w;
  vKind = aKind;
}`;

const LAND_FRAG = `
precision mediump float;
uniform vec3 uLow, uRock, uSnow, uTree, uFog, uLight, uSun, uSkyAmbient, uGround, uWaterColor;
uniform mediump float uMirror, uWater;
varying vec3 vNormal;
varying float vHeight, vDepth, vKind;
void main() {
  if (uMirror > 0.5 && vHeight < uWater) discard;
  vec3 n = normalize(vNormal);
  float steep = 1.0 - n.y;
  vec3 base = mix(uLow, uRock, smoothstep(0.22, 0.7, vHeight + steep * 0.55));
  base = mix(base, uSnow, smoothstep(0.92, 1.15, vHeight - steep * 0.4));
  base = mix(base, uTree, step(0.5, vKind));
  float diffuse = max(dot(n, normalize(uSun)), 0.0);
  vec3 ambient = mix(uGround, uSkyAmbient, n.y * 0.5 + 0.5);
  vec3 color = base * (ambient + uLight * diffuse);
  color = mix(color, uFog, smoothstep(4.0, 15.0, vDepth));
  if (uMirror > 0.5) color = mix(color, uWaterColor, 0.35);
  gl_FragColor = vec4(color, 1.0);
}`;

const WATER_VERT = `
attribute vec3 aPos;
uniform mat4 uMvp;
uniform float uShift;
varying vec3 vWorld;
varying float vDepth;
void main() {
  vec4 p = uMvp * vec4(aPos, 1.0);
  p.x += uShift * p.w;
  gl_Position = p;
  vWorld = aPos;
  vDepth = p.w;
}`;

const WATER_FRAG = `
precision mediump float;
uniform vec3 uWaterColor, uFog, uLight;
uniform float uTime;
varying vec3 vWorld;
varying float vDepth;
${NOISE}
void main() {
  float ripple = noise(vWorld.xz * vec2(5.0, 22.0) + vec2(uTime * 0.12, uTime * 0.05));
  vec3 color = mix(uWaterColor, uFog, smoothstep(3.0, 13.0, vDepth));
  color += uLight * pow(ripple, 7.0) * 0.5;
  gl_FragColor = vec4(color, 0.42 + 0.3 * ripple);
}`;

// Pins and trails share one small unlit program.
const MARK_VERT = `
attribute vec3 aPos;
attribute vec3 aNormal;
attribute float aDist;
uniform mat4 uMvp;
uniform float uShift, uScale;
uniform vec3 uOrigin;
varying float vDist, vShade;
void main() {
  vec4 p = uMvp * vec4(uOrigin + aPos * uScale, 1.0);
  p.x += uShift * p.w;
  gl_Position = p;
  vDist = aDist;
  vShade = 0.72 + 0.28 * max(dot(aNormal, normalize(vec3(0.4, 0.8, 0.45))), 0.0);
}`;

const MARK_FRAG = `
precision mediump float;
uniform vec3 uColor;
uniform float uReach, uDash, uTail;
varying float vDist, vShade;
void main() {
  if (vDist > uReach || (uTail > 0.0 && vDist < uReach - uTail)) discard;
  if (uDash > 0.0 && mod(vDist, uDash) > uDash * 0.55) discard;
  gl_FragColor = vec4(uColor * vShade, 1.0);
}`;

// Deterministic CPU noise so the range is the same on every visit.
function hash(x: number, z: number) {
  const s = Math.sin(x * 127.1 + z * 311.7) * 43758.5453;
  return s - Math.floor(s);
}
function noise(x: number, z: number) {
  const xi = Math.floor(x),
    zi = Math.floor(z);
  const xf = x - xi,
    zf = z - zi;
  const u = xf * xf * (3 - 2 * xf),
    v = zf * zf * (3 - 2 * zf);
  const a = hash(xi, zi),
    b = hash(xi + 1, zi),
    c = hash(xi, zi + 1),
    d = hash(xi + 1, zi + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
function ridged(x: number, z: number) {
  let sum = 0,
    amp = 0.5,
    freq = 1;
  for (let i = 0; i < 5; i++) {
    sum += (1 - Math.abs(noise(x * freq, z * freq) * 2 - 1)) * amp;
    amp *= 0.5;
    freq *= 2.1;
  }
  return sum;
}
// x, z, height, tightness
const PEAKS = [
  [0.2, -0.3, 1.75, 1.3],
  [-1.7, -1.0, 1.15, 1.2],
  [1.9, -1.3, 1.0, 1.4],
  [-0.5, -2.8, 1.3, 0.9],
  [3.4, -3.0, 1.2, 0.8],
  [-3.6, -2.6, 1.1, 0.8],
  [-3.4, -0.6, 0.55, 1.4],
  [3.2, 0.4, 0.45, 1.8],
];
function height(x: number, z: number) {
  let h = 0;
  for (const [px, pz, ph, tight] of PEAKS)
    h += Math.exp(-((x - px) ** 2 + (z - pz) ** 2) * tight) * ph;
  const r = ridged(x * 1.3 + 3, z * 1.3 + 7);
  h = h * (0.45 + 0.6 * r) + r * 0.1;
  // The lake basin, in front of the range.
  h -= Math.exp(-((x + 0.2) ** 2 * 0.12 + (z - 2.6) ** 2 * 0.3)) * 0.42;
  return h;
}

function buildLand() {
  const N = 110,
    SIZE = 7;
  const pos: number[] = [],
    nor: number[] = [],
    kind: number[] = [];
  const tri = (a: number[], b: number[], c: number[], k: number) => {
    const ux = b[0] - a[0],
      uy = b[1] - a[1],
      uz = b[2] - a[2];
    const vx = c[0] - a[0],
      vy = c[1] - a[1],
      vz = c[2] - a[2];
    let nx = uy * vz - uz * vy,
      ny = uz * vx - ux * vz,
      nz = ux * vy - uy * vx;
    const len = Math.hypot(nx, ny, nz) || 1;
    nx /= len;
    ny /= len;
    nz /= len;
    if (ny < 0 && k === 0) {
      nx = -nx;
      ny = -ny;
      nz = -nz;
    }
    pos.push(...a, ...b, ...c);
    for (let i = 0; i < 3; i++) {
      nor.push(nx, ny, nz);
      kind.push(k);
    }
  };
  const at = (i: number, j: number) => {
    const x = (i / N - 0.5) * 2 * SIZE,
      z = (j / N - 0.5) * 2 * SIZE;
    return [x, height(x, z), z];
  };
  for (let i = 0; i < N; i++) {
    for (let j = 0; j < N; j++) {
      const p00 = at(i, j),
        p10 = at(i + 1, j),
        p01 = at(i, j + 1),
        p11 = at(i + 1, j + 1);
      tri(p00, p01, p10, 0);
      tri(p10, p01, p11, 0);
    }
  }
  // Pines on the gentle lower slopes.
  for (let n = 0; n < 2600; n++) {
    const x = (hash(n, 1.7) - 0.5) * 9,
      z = (hash(n, 9.2) - 0.5) * 7 - 0.2;
    const y = height(x, z);
    if (y < WATER + 0.025 || y > 0.5) continue;
    if (x > -2.0 && x < -0.95 && z > 0.05 && z < 0.5) continue; // the town
    if (Math.hypot(x + 0.22, z - 0.53) < 0.2) continue; // the camp
    const slope =
      Math.hypot(height(x + 0.05, z) - y, height(x, z + 0.05) - y) / 0.05;
    if (slope > 0.9 || noise(x * 1.7, z * 1.7) < 0.42) continue;
    const tall = 0.1 + hash(n, 4.4) * 0.09,
      wide = tall * 0.3,
      turn = hash(n, 2.1) * 6.28;
    const tip = [x, y + tall, z];
    for (let s = 0; s < 5; s++) {
      const a0 = turn + (s / 5) * 6.2832,
        a1 = turn + ((s + 1) / 5) * 6.2832;
      tri(
        [x + Math.cos(a0) * wide, y - 0.01, z + Math.sin(a0) * wide],
        tip,
        [x + Math.cos(a1) * wide, y - 0.01, z + Math.sin(a1) * wide],
        1,
      );
    }
  }
  return {
    pos: new Float32Array(pos),
    nor: new Float32Array(nor),
    kind: new Float32Array(kind),
    count: pos.length / 3,
  };
}

type Route = {
  points: number[][];
  pins: number[];
  color: number[];
  dash: number;
  delay: number;
  seconds: number;
};

// Waypoints as [x, z]; `pins` are the indexes that get a map pin.
const ROUTES: Route[] = [
  {
    // Town, camp, the fork, and the summit.
    points: [
      [-1.33, 0.31],
      [-0.95, 0.4],
      [-0.32, 0.56],
      [0.1, 0.58],
      [0.7, 0.4],
      [0.5, 0.0],
      [0.2, -0.3],
    ],
    pins: [0, 2, 4, 6],
    color: [0.2, 0.83, 0.55],
    dash: 0,
    delay: 0.7,
    seconds: 3.8,
  },
  {
    points: [
      [0.7, 0.4],
      [1.15, 0.05],
      [1.6, -0.3],
      [1.85, -0.8],
      [1.9, -1.3],
    ],
    pins: [2, 4],
    color: [0.36, 0.62, 0.98],
    dash: 0.085,
    delay: 4.7,
    seconds: 2.2,
  },
];

// Pins that stand on their own: [x, z, planned?]
const LONE_PINS = [
  [-1.7, -1.0, 0],
  [-1.7, -0.2, 0],
  [2.9, 0.2, 1],
];
const LONE_DELAY = 7.0;

// The flight path: a shallow arc across the sky, right of the headline.
const FLIGHT_SECONDS = 26;
function flightAt(u: number) {
  return [-0.8 + u * 3.2, 1.3 + Math.sin(u * Math.PI) * 0.3, 1.3 - u * 1.0];
}
function buildFlight() {
  const pos: number[] = [],
    nor: number[] = [],
    dist: number[] = [];
  const STEPS = 160,
    HALF = 0.011;
  let total = 0;
  let prev = flightAt(0);
  for (let i = 1; i <= STEPS; i++) {
    const next = flightAt(i / STEPS);
    const step = Math.hypot(
      next[0] - prev[0],
      next[1] - prev[1],
      next[2] - prev[2],
    );
    const lo = (p: number[]) => [p[0], p[1] - HALF, p[2]],
      hi = (p: number[]) => [p[0], p[1] + HALF, p[2]];
    pos.push(
      ...lo(prev),
      ...hi(prev),
      ...lo(next),
      ...hi(prev),
      ...hi(next),
      ...lo(next),
    );
    dist.push(total, total, total + step, total, total + step, total + step);
    for (let k = 0; k < 6; k++) nor.push(0.4, 0.8, 0.45);
    total += step;
    prev = next;
  }
  return {
    pos: new Float32Array(pos),
    nor: new Float32Array(nor),
    dist: new Float32Array(dist),
    count: pos.length / 3,
    total,
  };
}
// A small airliner, nose toward +x: [x forward, y up, z right] per corner.
const PLANE_SHAPE: number[][][] = (() => {
  const nose = [0.5, 0, 0],
    tail = [-0.5, 0.03, 0];
  const mid = [
    [0.15, 0.07, 0],
    [0.15, 0, 0.06],
    [0.15, -0.06, 0],
    [0.15, 0, -0.06],
  ];
  const rear = [
    [-0.3, 0.055, 0],
    [-0.3, 0.01, 0.045],
    [-0.3, -0.03, 0],
    [-0.3, 0.01, -0.045],
  ];
  const tris: number[][][] = [];
  for (let i = 0; i < 4; i++) {
    const j = (i + 1) % 4;
    tris.push(
      [nose, mid[i], mid[j]],
      [mid[i], rear[i], mid[j]],
      [mid[j], rear[i], rear[j]],
      [rear[i], tail, rear[j]],
    );
  }
  for (const side of [1, -1]) {
    // Swept wing, then the tailplane.
    tris.push(
      [
        [0.14, -0.015, 0.05 * side],
        [-0.1, -0.015, 0.05 * side],
        [-0.12, 0.015, 0.5 * side],
      ],
      [
        [-0.1, -0.015, 0.05 * side],
        [-0.22, 0.015, 0.5 * side],
        [-0.12, 0.015, 0.5 * side],
      ],
      [
        [-0.34, 0.03, 0.03 * side],
        [-0.5, 0.03, 0.03 * side],
        [-0.5, 0.04, 0.19 * side],
      ],
    );
  }
  tris.push(
    [
      [-0.26, 0.05, 0],
      [-0.5, 0.03, 0],
      [-0.52, 0.22, 0],
    ],
    [
      [-0.26, 0.05, 0],
      [-0.52, 0.22, 0],
      [-0.43, 0.22, 0],
    ],
  );
  return tris;
})();
const PLANE_SIZE = 0.36;

/** The airliner at `u` along the flight path, pointing along it and banking a little. */
function planeAt(u: number) {
  const p = flightAt(u),
    q = flightAt(u + 0.01);
  let fx = q[0] - p[0],
    fy = q[1] - p[1],
    fz = q[2] - p[2];
  const fl = Math.hypot(fx, fy, fz);
  fx /= fl;
  fy /= fl;
  fz /= fl;
  const rl = Math.hypot(fz, fx) || 1;
  const bank = 0.22;
  // right = forward × world up, tipped down a little for the bank
  const rx = (-fz / rl) * Math.cos(bank),
    ry = -Math.sin(bank),
    rz = (fx / rl) * Math.cos(bank);
  const ux = ry * fz - rz * fy,
    uy = rz * fx - rx * fz,
    uz = rx * fy - ry * fx; // up = right × forward
  const pos: number[] = [],
    nor: number[] = [];
  for (const tri of PLANE_SHAPE) {
    const w = tri.map(([x, y, z]) => [
      p[0] + (fx * x + ux * y + rx * z) * PLANE_SIZE,
      p[1] + (fy * x + uy * y + ry * z) * PLANE_SIZE,
      p[2] + (fz * x + uz * y + rz * z) * PLANE_SIZE,
    ]);
    const ax = w[1][0] - w[0][0],
      ay = w[1][1] - w[0][1],
      az = w[1][2] - w[0][2];
    const bx = w[2][0] - w[0][0],
      by = w[2][1] - w[0][1],
      bz = w[2][2] - w[0][2];
    let nx = ay * bz - az * by,
      ny = az * bx - ax * bz,
      nz = ax * by - ay * bx;
    const len = Math.hypot(nx, ny, nz) || 1;
    if (ny < 0) {
      nx = -nx;
      ny = -ny;
      nz = -nz;
    }
    for (const corner of w) {
      pos.push(...corner);
      nor.push(nx / len, ny / len, nz / len);
    }
  }
  return {
    pos: new Float32Array(pos),
    nor: new Float32Array(nor),
    count: pos.length / 3,
  };
}

type Tri = number[][];
type Mesh = { pos: Float32Array; nor: Float32Array; count: number };

/** Flat-shaded triangles with upward-leaning face normals. */
function flatMesh(tris: Tri[]): Mesh {
  const pos: number[] = [],
    nor: number[] = [];
  for (const [a, b, c] of tris) {
    const ux = b[0] - a[0],
      uy = b[1] - a[1],
      uz = b[2] - a[2];
    const vx = c[0] - a[0],
      vy = c[1] - a[1],
      vz = c[2] - a[2];
    let nx = uy * vz - uz * vy,
      ny = uz * vx - ux * vz,
      nz = ux * vy - uy * vx;
    const len = Math.hypot(nx, ny, nz) || 1;
    if (ny < 0 || (ny === 0 && nz < 0)) {
      nx = -nx;
      ny = -ny;
      nz = -nz;
    }
    pos.push(...a, ...b, ...c);
    for (let i = 0; i < 3; i++) nor.push(nx / len, ny / len, nz / len);
  }
  return {
    pos: new Float32Array(pos),
    nor: new Float32Array(nor),
    count: pos.length / 3,
  };
}
/** A box standing on y0, centered on (cx, cz): four walls and a top. */
function box(
  cx: number,
  y0: number,
  cz: number,
  w: number,
  h: number,
  d: number,
): Tri[] {
  const x0 = cx - w / 2,
    x1 = cx + w / 2,
    z0 = cz - d / 2,
    z1 = cz + d / 2,
    y1 = y0 + h;
  const quad = (a: number[], b: number[], c: number[], e: number[]): Tri[] => [
    [a, b, c],
    [a, c, e],
  ];
  return [
    ...quad([x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]),
    ...quad([x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0]),
    ...quad([x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0]),
    ...quad([x1, y0, z0], [x1, y0, z1], [x1, y1, z1], [x1, y1, z0]),
    ...quad([x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1]),
  ];
}
/** A gable roof over a box top, ridge running left to right. */
function gable(
  cx: number,
  y: number,
  cz: number,
  w: number,
  rise: number,
  d: number,
): Tri[] {
  const x0 = cx - w / 2 - 0.008,
    x1 = cx + w / 2 + 0.008,
    z0 = cz - d / 2 - 0.008,
    z1 = cz + d / 2 + 0.008;
  const l = [x0, y + rise, cz],
    r = [x1, y + rise, cz];
  return [
    [[x0, y, z1], [x1, y, z1], r],
    [[x0, y, z1], r, l],
    [[x0, y, z0], [x1, y, z0], r],
    [[x0, y, z0], r, l],
    [[x0, y, z0], [x0, y, z1], l],
    [[x1, y, z0], [x1, y, z1], r],
  ];
}

// A tent pitched beside the trail, door toward the lake.
const CAMP = [-0.17, 0.5];
const CAMP_PIN = 1; // which pin on the first route marks the camp
function buildTent() {
  const W = 0.075,
    H = 0.1,
    L = 0.09;
  const rf = [0, H, L],
    rb = [0, H, -L];
  const fl = [-W, 0, L],
    fr = [W, 0, L],
    bl = [-W, 0, -L],
    br = [W, 0, -L];
  return {
    body: flatMesh([
      [fl, rf, rb],
      [fl, rb, bl],
      [fr, rb, rf],
      [fr, br, rb],
      [bl, rb, br],
      [fl, fr, rf],
    ]),
    door: flatMesh([
      [
        [-W * 0.42, 0, L + 0.003],
        [W * 0.42, 0, L + 0.003],
        [0, H * 0.72, L + 0.003],
      ],
    ]),
    // A campfire: one small flame beside the tent.
    fire: flatMesh(
      [0, 1, 2, 3].map((i) => {
        const a = (i / 4) * Math.PI * 2,
          b = ((i + 1) / 4) * Math.PI * 2;
        return [
          [Math.cos(a) * 0.018, 0, Math.sin(a) * 0.018],
          [Math.cos(b) * 0.018, 0, Math.sin(b) * 0.018],
          [0, 0.055, 0],
        ];
      }),
    ),
  };
}

/**
 * The lakeside town where the trail starts: a hotel, a few houses, and a dock
 * with a boat. Buildings are [x, z, width, wall height, depth, window columns, floors].
 */
const BUILDINGS = [
  [-1.47, 0.2, 0.24, 0.17, 0.12, 5, 3], // the hotel
  [-1.7, 0.31, 0.1, 0.07, 0.085, 2, 1],
  [-1.19, 0.3, 0.1, 0.07, 0.085, 2, 1],
  [-1.53, 0.37, 0.085, 0.06, 0.075, 2, 1],
  [-1.07, 0.2, 0.1, 0.075, 0.085, 2, 1],
  [-1.84, 0.19, 0.1, 0.07, 0.085, 2, 1],
  [-1.24, 0.14, 0.11, 0.08, 0.085, 2, 1],
];
function buildTown() {
  const walls: Tri[] = [],
    roofs: Tri[] = [],
    windows: Tri[] = [],
    wood: Tri[] = [],
    boat: Tri[] = [];
  for (const [x, z, w, h, d, cols, floors] of BUILDINGS) {
    const y0 =
      Math.min(
        ground(x - w / 2, z + d / 2),
        ground(x + w / 2, z + d / 2),
        ground(x, z),
      ) - 0.01;
    walls.push(...box(x, y0, z, w, h + 0.01, d));
    roofs.push(...gable(x, y0 + h + 0.01, z, w, 0.05, d));
    const front = z + d / 2 + 0.002;
    for (let f = 0; f < floors; f++) {
      for (let c = 0; c < cols; c++) {
        const wx = x - w / 2 + ((c + 0.5) / cols) * w,
          wy = y0 + 0.03 + (f / floors) * h;
        const s = (w / cols) * 0.26;
        windows.push(
          [
            [wx - s, wy, front],
            [wx + s, wy, front],
            [wx + s, wy + s * 2.2, front],
          ],
          [
            [wx - s, wy, front],
            [wx + s, wy + s * 2.2, front],
            [wx - s, wy + s * 2.2, front],
          ],
        );
      }
    }
  }
  // The dock runs out from the shore, with posts and a landing at the end.
  const DX = -1.36,
    deck = WATER + 0.02;
  wood.push(
    ...box(DX, deck, 0.63, 0.05, 0.01, 0.44),
    ...box(DX, deck, 0.87, 0.17, 0.01, 0.05),
  );
  for (const z of [0.5, 0.62, 0.74, 0.86]) {
    wood.push(
      ...box(DX - 0.03, WATER - 0.03, z, 0.012, 0.07, 0.012),
      ...box(DX + 0.03, WATER - 0.03, z, 0.012, 0.07, 0.012),
    );
  }
  // A small boat tied up alongside.
  const bx = DX + 0.12,
    bz = 0.72,
    y = WATER,
    top = WATER + 0.028;
  const bow = [bx, top, bz + 0.085],
    stern = [
      [bx - 0.028, top, bz - 0.06],
      [bx + 0.028, top, bz - 0.06],
    ];
  const keel = [
    [bx, y - 0.005, bz + 0.05],
    [bx, y - 0.005, bz - 0.05],
  ];
  boat.push(
    [bow, stern[0], keel[0]],
    [stern[0], keel[1], keel[0]],
    [bow, stern[1], keel[0]],
    [stern[1], keel[1], keel[0]],
    [stern[0], stern[1], keel[1]],
  );
  return {
    walls: flatMesh(walls),
    roofs: flatMesh(roofs),
    windows: flatMesh(windows),
    wood: flatMesh(wood),
    boat: flatMesh(boat),
  };
}

const ground = (x: number, z: number) => Math.max(height(x, z), WATER);

/** A ribbon that follows the ground along a route, with distance along it. */
function buildTrail(route: Route) {
  const pos: number[] = [],
    nor: number[] = [],
    dist: number[] = [],
    pinAt: number[] = [];
  const samples: number[][] = [];
  let total = 0;
  for (let i = 0; i < route.points.length - 1; i++) {
    const [ax, az] = route.points[i],
      [bx, bz] = route.points[i + 1];
    const steps = Math.ceil(Math.hypot(bx - ax, bz - az) / 0.04);
    if (route.pins.includes(i)) pinAt.push(total);
    for (let s = 0; s < steps; s++) {
      const t = s / steps;
      const x = ax + (bx - ax) * t,
        z = az + (bz - az) * t;
      samples.push([x, z, total + Math.hypot(bx - ax, bz - az) * t]);
    }
    total += Math.hypot(bx - ax, bz - az);
  }
  const last = route.points[route.points.length - 1];
  samples.push([last[0], last[1], total]);
  if (route.pins.includes(route.points.length - 1)) pinAt.push(total);

  const HALF = 0.016,
    LIFT = 0.028;
  const edge = (i: number) => {
    const a = samples[Math.max(i - 1, 0)],
      b = samples[Math.min(i + 1, samples.length - 1)];
    const len = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
    const sx = (-(b[1] - a[1]) / len) * HALF,
      sz = ((b[0] - a[0]) / len) * HALF;
    const [x, z] = samples[i];
    return [
      [x - sx, ground(x - sx, z - sz) + LIFT, z - sz],
      [x + sx, ground(x + sx, z + sz) + LIFT, z + sz],
    ];
  };
  for (let i = 0; i < samples.length - 1; i++) {
    const [l0, r0] = edge(i),
      [l1, r1] = edge(i + 1);
    const d0 = samples[i][2],
      d1 = samples[i + 1][2];
    pos.push(...l0, ...r0, ...l1, ...r0, ...r1, ...l1);
    dist.push(d0, d0, d1, d0, d1, d1);
    for (let k = 0; k < 6; k++) nor.push(0, 1, 0);
  }
  return {
    pos: new Float32Array(pos),
    nor: new Float32Array(nor),
    dist: new Float32Array(dist),
    count: pos.length / 3,
    total,
    pinAt,
    pins: route.pins.map((i) => [
      route.points[i][0],
      ground(route.points[i][0], route.points[i][1]),
      route.points[i][1],
    ]),
  };
}

/** A low-poly map pin: a round head on a point, standing on the origin. */
function buildPin() {
  const pos: number[] = [],
    nor: number[] = [];
  const tri = (a: number[], b: number[], c: number[]) => {
    const ux = b[0] - a[0],
      uy = b[1] - a[1],
      uz = b[2] - a[2];
    const vx = c[0] - a[0],
      vy = c[1] - a[1],
      vz = c[2] - a[2];
    let nx = uy * vz - uz * vy,
      ny = uz * vx - ux * vz,
      nz = ux * vy - uy * vx;
    const len = Math.hypot(nx, ny, nz) || 1;
    pos.push(...a, ...b, ...c);
    for (let i = 0; i < 3; i++) nor.push(nx / len, ny / len, nz / len);
  };
  const SIDES = 8,
    RINGS = 5,
    R = 0.34,
    CY = 0.66;
  const ring = (r: number) => {
    // r = 0 is the bottom of the head, RINGS the top.
    const phi = (r / RINGS) * Math.PI;
    return (s: number) => {
      const a = (s / SIDES) * Math.PI * 2;
      return [
        Math.sin(phi) * Math.cos(a) * R,
        CY - Math.cos(phi) * R,
        Math.sin(phi) * Math.sin(a) * R,
      ];
    };
  };
  for (let s = 0; s < SIDES; s++) {
    // The point, from the ground up to the widest ring.
    const mid = ring(2);
    tri([0, 0, 0], mid(s + 1), mid(s));
    for (let r = 2; r < RINGS; r++) {
      const lo = ring(r),
        hi = ring(r + 1);
      tri(lo(s), lo(s + 1), hi(s));
      tri(lo(s + 1), hi(s + 1), hi(s));
    }
  }
  return {
    pos: new Float32Array(pos),
    nor: new Float32Array(nor),
    count: pos.length / 3,
  };
}

function perspective(fovy: number, aspect: number, near: number, far: number) {
  const f = 1 / Math.tan(fovy / 2),
    nf = 1 / (near - far);
  return [
    f / aspect,
    0,
    0,
    0,
    0,
    f,
    0,
    0,
    0,
    0,
    (far + near) * nf,
    -1,
    0,
    0,
    2 * far * near * nf,
    0,
  ];
}
function lookAt(e: number[], t: number[]) {
  let zx = e[0] - t[0],
    zy = e[1] - t[1],
    zz = e[2] - t[2];
  const zl = Math.hypot(zx, zy, zz);
  zx /= zl;
  zy /= zl;
  zz /= zl;
  let xx = zz,
    xz = -zx; // cross(up, z) with up = (0, 1, 0)
  const xl = Math.hypot(xx, xz);
  xx /= xl;
  xz /= xl;
  const yx = zy * xz,
    yy = zz * xx - zx * xz,
    yz = -zy * xx;
  return [
    xx,
    yx,
    zx,
    0,
    0,
    yy,
    zy,
    0,
    xz,
    yz,
    zz,
    0,
    -(xx * e[0] + xz * e[2]),
    -(yx * e[0] + yy * e[1] + yz * e[2]),
    -(zx * e[0] + zy * e[1] + zz * e[2]),
    1,
  ];
}
function multiply(a: number[], b: number[]) {
  const out = new Array(16).fill(0);
  for (let c = 0; c < 4; c++)
    for (let r = 0; r < 4; r++)
      for (let k = 0; k < 4; k++) out[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k];
  return out;
}

onMounted(() => {
  const el = canvas.value;
  if (!el) return;
  const gl = el.getContext("webgl", { alpha: false, antialias: true });
  if (!gl) return;

  const link = (vert: string, frag: string) => {
    const program = gl.createProgram()!;
    for (const [type, source] of [
      [gl.VERTEX_SHADER, vert],
      [gl.FRAGMENT_SHADER, frag],
    ] as const) {
      const shader = gl.createShader(type)!;
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      gl.attachShader(program, shader);
    }
    gl.linkProgram(program);
    return gl.getProgramParameter(program, gl.LINK_STATUS) ? program : null;
  };
  const sky = link(SKY_VERT, SKY_FRAG);
  const land = link(LAND_VERT, LAND_FRAG);
  const water = link(WATER_VERT, WATER_FRAG);
  const mark = link(MARK_VERT, MARK_FRAG);
  if (!sky || !land || !water || !mark) return;

  const buffer = (data: Float32Array) => {
    const b = gl.createBuffer()!;
    gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    return b;
  };
  const mesh = buildLand();
  const buffers = {
    corner: buffer(new Float32Array([-1, -1, 3, -1, -1, 3])),
    pos: buffer(mesh.pos),
    nor: buffer(mesh.nor),
    kind: buffer(mesh.kind),
    water: buffer(
      new Float32Array([
        -40,
        WATER,
        -40,
        40,
        WATER,
        -40,
        -40,
        WATER,
        40,
        40,
        WATER,
        -40,
        40,
        WATER,
        40,
        -40,
        WATER,
        40,
      ]),
    ),
  };
  const pin = buildPin();
  const pinBuffers = { pos: buffer(pin.pos), nor: buffer(pin.nor) };
  const trails = ROUTES.map((route) => {
    const trail = buildTrail(route);
    return {
      route,
      trail,
      pos: buffer(trail.pos),
      nor: buffer(trail.nor),
      dist: buffer(trail.dist),
    };
  });
  const flight = buildFlight();
  const flightBuffers = {
    pos: buffer(flight.pos),
    nor: buffer(flight.nor),
    dist: buffer(flight.dist),
  };
  const planeBuffers = { pos: gl.createBuffer()!, nor: gl.createBuffer()! };
  const tent = buildTent();
  const tentBuffers = {
    body: {
      pos: buffer(tent.body.pos),
      nor: buffer(tent.body.nor),
      count: tent.body.count,
    },
    door: {
      pos: buffer(tent.door.pos),
      nor: buffer(tent.door.nor),
      count: tent.door.count,
    },
    fire: {
      pos: buffer(tent.fire.pos),
      nor: buffer(tent.fire.nor),
      count: tent.fire.count,
    },
  };
  const camp = [CAMP[0], ground(CAMP[0], CAMP[1]) - 0.008, CAMP[1]];
  const town = buildTown();
  const townBuffers = Object.fromEntries(
    Object.entries(town).map(([name, mesh]) => [
      name,
      { pos: buffer(mesh.pos), nor: buffer(mesh.nor), count: mesh.count },
    ]),
  ) as Record<
    keyof typeof town,
    { pos: WebGLBuffer; nor: WebGLBuffer; count: number }
  >;
  const lonePins = LONE_PINS.map(([x, z, planned]) => ({
    origin: [x, ground(x, z), z],
    planned,
  }));
  const bind = (
    program: WebGLProgram,
    name: string,
    b: WebGLBuffer,
    size: number,
  ) => {
    const location = gl.getAttribLocation(program, name);
    gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.enableVertexAttribArray(location);
    gl.vertexAttribPointer(location, size, gl.FLOAT, false, 0, 0);
  };
  const set = (
    program: WebGLProgram,
    values: Record<string, number | number[]>,
  ) => {
    for (const name in values) {
      const value = values[name],
        location = gl.getUniformLocation(program, name);
      if (typeof value === "number") gl.uniform1f(location, value);
      else if (value.length === 2) gl.uniform2fv(location, value);
      else if (value.length === 3) gl.uniform3fv(location, value);
      else gl.uniformMatrix4fv(location, false, new Float32Array(value));
    }
  };

  const root = document.documentElement;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  const start = performance.now();
  let visible = true,
    frame = 0;
  let lookX = 0,
    lookY = 0,
    aimX = 0,
    aimY = 0;

  const draw = () => {
    frame = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.round(el.clientWidth * dpr),
      h = Math.round(el.clientHeight * dpr);
    if (!w || !h) return;
    if (el.width !== w || el.height !== h) {
      el.width = w;
      el.height = h;
    }
    gl.viewport(0, 0, w, h);

    const dark = root.classList.contains("dark");
    const palette = PALETTES[dark ? "dark" : "light"];
    const still = reduced.matches;
    const time = still ? 12 : (performance.now() - start) / 1000;
    lookX += (aimX - lookX) * 0.04;
    lookY += (aimY - lookY) * 0.04;

    const aspect = w / h,
      wide = aspect > 1.25;
    const shift = wide ? 0.36 : 0;
    const angle = 0.12 + Math.sin(time * 0.05) * 0.16 + lookX * 0.1;
    const eye = [
      Math.sin(angle) * 5.6,
      0.5 + lookY * 0.12,
      Math.cos(angle) * 5.6,
    ];
    const mvp = multiply(
      perspective(wide ? 0.6 : 1.0, aspect, 0.1, 60),
      lookAt(eye, [0.2, wide ? 0.6 : 2.5, 0]),
    );

    gl.disable(gl.BLEND);
    gl.disable(gl.DEPTH_TEST);
    gl.useProgram(sky);
    bind(sky, "aCorner", buffers.corner, 2);
    set(sky, {
      uTime: time,
      uDark: dark ? 1 : 0,
      uAspect: aspect,
      uWide: wide ? 1 : 0,
      uSunAt: wide ? [0.83, 0.5] : [0.72, 0.56],
    });
    gl.drawArrays(gl.TRIANGLES, 0, 3);

    gl.enable(gl.DEPTH_TEST);
    gl.useProgram(land);
    bind(land, "aPos", buffers.pos, 3);
    bind(land, "aNormal", buffers.nor, 3);
    bind(land, "aKind", buffers.kind, 1);
    set(land, {
      uMvp: mvp,
      uShift: shift,
      uWater: WATER,
      uLow: palette.low,
      uRock: palette.rock,
      uSnow: palette.snow,
      uTree: palette.tree,
      uFog: palette.fog,
      uLight: palette.light,
      uSun: palette.sun,
      uSkyAmbient: palette.skyAmbient,
      uGround: palette.ground,
      uWaterColor: palette.water,
    });
    // The range mirrored in the lake, then the range itself.
    gl.clear(gl.DEPTH_BUFFER_BIT);
    set(land, { uMirror: 1 });
    gl.drawArrays(gl.TRIANGLES, 0, mesh.count);
    gl.clear(gl.DEPTH_BUFFER_BIT);
    set(land, { uMirror: 0 });
    gl.drawArrays(gl.TRIANGLES, 0, mesh.count);
    gl.disableVertexAttribArray(gl.getAttribLocation(land, "aNormal"));
    gl.disableVertexAttribArray(gl.getAttribLocation(land, "aKind"));

    // Trails draw themselves in, and each pin drops as the trail reaches it.
    gl.useProgram(mark);
    const distAt = gl.getAttribLocation(mark, "aDist");
    for (const { route, trail, pos, nor, dist } of trails) {
      const reach =
        Math.min(Math.max((time - route.delay) / route.seconds, 0), 1) *
        trail.total;
      const tint = route.color.map((c) => c * (dark ? 0.9 : 1));
      bind(mark, "aPos", pos, 3);
      bind(mark, "aNormal", nor, 3);
      bind(mark, "aDist", dist, 1);
      set(mark, {
        uMvp: mvp,
        uShift: shift,
        uScale: 1,
        uOrigin: [0, 0, 0],
        uColor: route.dash ? tint : dark ? [0.86, 0.9, 0.86] : [1, 0.98, 0.92],
        uReach: reach,
        uDash: route.dash,
        uTail: 0,
      });
      gl.drawArrays(gl.TRIANGLES, 0, trail.count);

      gl.disableVertexAttribArray(distAt);
      gl.vertexAttrib1f(distAt, 0);
      bind(mark, "aPos", pinBuffers.pos, 3);
      bind(mark, "aNormal", pinBuffers.nor, 3);
      trail.pins.forEach((origin, i) => {
        const reachedAt =
          route.delay + (trail.pinAt[i] / trail.total) * route.seconds;
        const k = Math.min(Math.max((time - reachedAt) / 0.55, 0), 1);
        if (k <= 0) return;
        const pop = 1 + 2.7 * Math.pow(k - 1, 3) + 1.7 * Math.pow(k - 1, 2); // ease-out with overshoot
        set(mark, {
          uScale: 0.2 * pop,
          uOrigin: [origin[0], origin[1] + (1 - k) * 0.25, origin[2]],
          uColor: tint,
          uReach: 1,
          uDash: 0,
          uTail: 0,
        });
        gl.drawArrays(gl.TRIANGLES, 0, pin.count);
      });
    }
    // A few places off the route, once the trails are drawn.
    lonePins.forEach(({ origin, planned }, i) => {
      const k = Math.min(Math.max((time - LONE_DELAY - i * 0.35) / 0.55, 0), 1);
      if (k <= 0) return;
      const pop = 1 + 2.7 * Math.pow(k - 1, 3) + 1.7 * Math.pow(k - 1, 2);
      set(mark, {
        uScale: 0.2 * pop,
        uOrigin: [origin[0], origin[1] + (1 - k) * 0.25, origin[2]],
        uColor: ROUTES[planned].color.map((c) => c * (dark ? 0.9 : 1)),
        uReach: 1,
        uDash: 0,
        uTail: 0,
      });
      gl.drawArrays(gl.TRIANGLES, 0, pin.count);
    });

    // The town and the camp. Windows and the campfire glow after dark.
    for (const [part, color] of [
      [townBuffers.walls, dark ? [0.2, 0.24, 0.27] : [0.98, 0.95, 0.88]],
      [townBuffers.roofs, dark ? [0.2, 0.11, 0.1] : [0.72, 0.33, 0.24]],
      [townBuffers.windows, dark ? [1.5, 1.1, 0.5] : [0.3, 0.38, 0.45]],
      [townBuffers.wood, dark ? [0.13, 0.1, 0.08] : [0.5, 0.36, 0.24]],
      [townBuffers.boat, dark ? [0.3, 0.33, 0.36] : [0.95, 0.93, 0.9]],
    ] as const) {
      bind(mark, "aPos", part.pos, 3);
      bind(mark, "aNormal", part.nor, 3);
      set(mark, {
        uScale: 1,
        uOrigin: [0, 0, 0],
        uColor: [...color],
        uReach: 1,
        uDash: 0,
        uTail: 0,
      });
      gl.drawArrays(gl.TRIANGLES, 0, part.count);
    }
    // The tent goes up as the trail reaches its pin.
    const first = trails[0];
    const campAt =
      first.route.delay +
      (first.trail.pinAt[CAMP_PIN] / first.trail.total) * first.route.seconds;
    const pitched = Math.min(Math.max((time - campAt) / 0.55, 0), 1);
    if (pitched > 0) {
      const pop =
        1 + 2.7 * Math.pow(pitched - 1, 3) + 1.7 * Math.pow(pitched - 1, 2);
      for (const [part, color] of [
        [tentBuffers.body, dark ? [0.62, 0.3, 0.12] : [0.93, 0.5, 0.16]],
        [tentBuffers.door, dark ? [0.1, 0.06, 0.04] : [0.3, 0.17, 0.1]],
      ] as const) {
        bind(mark, "aPos", part.pos, 3);
        bind(mark, "aNormal", part.nor, 3);
        set(mark, {
          uScale: pop,
          uOrigin: camp,
          uColor: [...color],
          uReach: 1,
          uDash: 0,
          uTail: 0,
        });
        gl.drawArrays(gl.TRIANGLES, 0, part.count);
      }
      bind(mark, "aPos", tentBuffers.fire.pos, 3);
      bind(mark, "aNormal", tentBuffers.fire.nor, 3);
      set(mark, {
        uScale: pop * (1 + 0.12 * Math.sin(time * 7)),
        uOrigin: [
          camp[0] + 0.13,
          ground(camp[0] + 0.13, camp[2] + 0.05),
          camp[2] + 0.05,
        ],
        uColor: dark ? [1.6, 0.8, 0.25] : [1, 0.55, 0.15],
      });
      gl.drawArrays(gl.TRIANGLES, 0, tentBuffers.fire.count);
    }

    // The plane and the dashed line it leaves behind.
    const flown = still
      ? 0.55
      : ((time + 6) % FLIGHT_SECONDS) / (FLIGHT_SECONDS * 0.8);
    if (flown < 1) {
      const paper = dark ? [0.8, 0.86, 0.9] : [1, 0.99, 0.96];
      bind(mark, "aPos", flightBuffers.pos, 3);
      bind(mark, "aNormal", flightBuffers.nor, 3);
      bind(mark, "aDist", flightBuffers.dist, 1);
      set(mark, {
        uScale: 1,
        uOrigin: [0, 0, 0],
        uColor: paper,
        uReach: flown * flight.total - 0.22,
        uDash: 0.1,
        uTail: 1.5,
      });
      gl.drawArrays(gl.TRIANGLES, 0, flight.count);

      const plane = planeAt(flown);
      gl.disableVertexAttribArray(distAt);
      gl.vertexAttrib1f(distAt, 0);
      for (const [name, data, b] of [
        ["aPos", plane.pos, planeBuffers.pos],
        ["aNormal", plane.nor, planeBuffers.nor],
      ] as const) {
        gl.bindBuffer(gl.ARRAY_BUFFER, b);
        gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);
        bind(mark, name, b, 3);
      }
      set(mark, { uReach: 1, uDash: 0, uTail: 0 });
      gl.drawArrays(gl.TRIANGLES, 0, plane.count);
    }
    gl.disableVertexAttribArray(gl.getAttribLocation(mark, "aNormal"));

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.useProgram(water);
    bind(water, "aPos", buffers.water, 3);
    set(water, {
      uMvp: mvp,
      uShift: shift,
      uTime: time,
      uWaterColor: palette.water,
      uFog: palette.fog,
      uLight: palette.light,
    });
    gl.drawArrays(gl.TRIANGLES, 0, 6);

    if (visible && !still) frame = requestAnimationFrame(draw);
  };
  const redraw = () => {
    if (!frame) frame = requestAnimationFrame(draw);
  };

  const onPointer = (event: PointerEvent) => {
    if (reduced.matches || event.pointerType === "touch") return;
    aimX = (event.clientX / window.innerWidth) * 2 - 1;
    aimY = (event.clientY / window.innerHeight) * 2 - 1;
  };
  const themeWatch = new MutationObserver(redraw);
  themeWatch.observe(root, { attributes: true, attributeFilter: ["class"] });
  const sizeWatch = new ResizeObserver(redraw);
  sizeWatch.observe(el);
  const viewWatch = new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    if (visible) redraw();
  });
  viewWatch.observe(el);
  reduced.addEventListener("change", redraw);
  window.addEventListener("pointermove", onPointer, { passive: true });
  el.classList.add("is-ready");
  redraw();

  dispose = () => {
    cancelAnimationFrame(frame);
    themeWatch.disconnect();
    sizeWatch.disconnect();
    viewWatch.disconnect();
    reduced.removeEventListener("change", redraw);
    window.removeEventListener("pointermove", onPointer);
    gl.getExtension("WEBGL_lose_context")?.loseContext();
  };
});

onBeforeUnmount(() => dispose());
</script>

<template>
  <canvas ref="canvas" class="al-scene" aria-hidden="true" />
</template>
