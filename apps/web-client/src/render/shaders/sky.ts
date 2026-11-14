import { NOISE } from "./common";

export const SHELL_VERTEX = /* glsl */ `
varying vec3 vPos;
void main(){ vPos = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;

/** Limb glow: optical depth approximated from the closest approach of the view ray to the planet center. Stylized. */
export const ATMOSPHERE_FRAGMENT = /* glsl */ `
precision highp float;
varying vec3 vPos;
uniform vec3 uSunDir; uniform vec3 uCamPos; uniform vec3 uSkyColor; uniform float uAtmo; uniform float uScale; uniform float uErosion; uniform float uTime; uniform float uSunDim;
${NOISE}
void main(){
  vec3 d = normalize(vPos - uCamPos);
  float t = -dot(uCamPos, d);
  vec3 pc = uCamPos + d * t;
  float b = length(pc);
  vec3 pn = pc / max(b, 1e-4);
  float sun = dot(pn, uSunDir);
  float dayf = smoothstep(-0.3, 0.35, sun);
  float a = exp(-max(b - 1.0, 0.0) / uScale) * smoothstep(0.992, 1.004, b) * uAtmo * 1.5;
  float dusk = smoothstep(-0.35, -0.05, sun) * smoothstep(0.2, -0.05, sun);
  vec3 col = mix(uSkyColor, vec3(1.0, 0.5, 0.25), dusk * 0.45) * (0.04 + 0.96 * dayf) * uSunDim * 1.15;
  // Weak magnetic field: wisps of atmosphere leaking away from the star.
  float tail = uErosion * smoothstep(0.1, -0.7, sun) * exp(-max(b - 1.0, 0.0) / (uScale * 5.0)) * step(1.0, b);
  float wisp = fbm(pc * 5.0 + vec3(0.0, 0.0, uTime * 0.05));
  a += tail * smoothstep(0.35, 0.75, wisp) * 0.5;
  col = mix(col, uSkyColor * 0.8 + 0.15, clamp(tail, 0.0, 1.0));
  gl_FragColor = vec4(col, clamp(a, 0.0, 1.0));
}`;

export const CLOUD_FRAGMENT = /* glsl */ `
precision highp float;
varying vec4 vA; varying vec4 vD; varying vec3 vDir;
uniform vec3 uSunDir; uniform vec3 uCloudColor; uniform vec3 uStarColor; uniform float uCloudOpacity; uniform float uTime; uniform float uSeed; uniform float uFlash; uniform float uSunDim;
uniform vec4 uStorms[3];
${NOISE}
void main(){
  vec3 n = normalize(vDir);
  vec3 q = n * 6.5 + vec3(uTime * 0.011, 0.0, uTime * 0.007) + uSeed;
#if OCTAVES > 2
  q += 1.1 * vec3(vnoise(n * 3.5 + uTime * 0.008), vnoise(n * 3.5 + 7.3), vnoise(n * 3.5 + 13.1));
#endif
  float base = fbm(q);
  float fine = vnoise(n * 34.0 + uSeed + uTime * 0.012);
  float w = smoothstep(0.32, 0.70, base) * 0.8 + 0.2 * fine;
  float cover = clamp(vA.w, 0.0, 1.0);
  float edge = 1.05 - cover * 1.08;
  float a = smoothstep(edge, edge + 0.34, w) * (0.55 + 0.45 * fine) * (0.6 + 0.4 * smoothstep(0.4, 0.75, base));
  a = mix(a, 1.0, smoothstep(0.88, 1.0, cover));
  float storm = 0.0;
  for (int i = 0; i < 3; i++) {
    float s = uStorms[i].w;
    if (s <= 0.0) continue;
    vec3 c = uStorms[i].xyz;
    float r = acos(clamp(dot(n, c), -1.0, 1.0));
    vec3 e1 = normalize(cross(c, vec3(0.31, 0.9, 0.29))), e2 = cross(c, e1);
    float th = atan(dot(n, e2), dot(n, e1));
    float arms = 0.5 + 0.5 * sin(th * 2.0 + log(r * 60.0 + 1.0) * 5.0 - uTime * 0.5);
    float fall = smoothstep(0.24, 0.02, r);
    storm = max(storm, s * fall * (0.35 + 0.65 * arms) * smoothstep(0.004, 0.02, r));
  }
  a = max(a, storm);
  float day = smoothstep(-0.12, 0.3, dot(n, uSunDir));
  vec3 col = uCloudColor * uStarColor * (0.07 + 0.93 * day) * uSunDim * (0.78 + 0.22 * base);
  col += vec3(0.75, 0.82, 1.0) * uFlash * clamp(vD.y, 0.0, 1.0) * smoothstep(0.55, 0.9, vnoise(n * 22.0 + floor(uTime * 0.7)));
  gl_FragColor = vec4(col, a * uCloudOpacity);
}`;

export const AURORA_VERTEX = /* glsl */ `
varying vec2 vUv; varying vec3 vPos;
void main(){ vUv = uv; vPos = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
export const AURORA_FRAGMENT = /* glsl */ `
precision highp float;
varying vec2 vUv; varying vec3 vPos;
uniform float uAurora; uniform float uTime; uniform vec3 uSunDir;
${NOISE}
void main(){
  float ang = vUv.x * 6.2831853;
  vec3 p = vec3(cos(ang) * 3.0, sin(ang) * 3.0, uTime * 0.12);
  float ribbon = smoothstep(0.45, 0.8, fbm(p + vec3(0.0, 0.0, vUv.y * 0.6)));
  float vertical = smoothstep(0.0, 0.15, vUv.y) * (1.0 - smoothstep(0.25, 1.0, vUv.y));
  float night = smoothstep(0.35, -0.35, dot(normalize(vPos), uSunDir));
  vec3 col = mix(vec3(0.25, 1.0, 0.55), vec3(0.65, 0.4, 1.0), vUv.y);
  gl_FragColor = vec4(col, ribbon * vertical * uAurora * (0.25 + 0.75 * night) * 0.85);
}`;

export const SUN_FRAGMENT = /* glsl */ `
precision highp float;
varying vec2 vUv; uniform vec3 uStarColor; uniform float uSunDim;
void main(){
  float r = length(vUv - 0.5) * 2.0;
  float core = smoothstep(0.26, 0.2, r);
  float halo = pow(max(0.0, 1.0 - r), 3.0);
  gl_FragColor = vec4(uStarColor * (core * 1.4 + halo * 0.9), (core + halo * 0.8) * uSunDim);
}`;
export const UV_VERTEX = /* glsl */ `
varying vec2 vUv;
void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
