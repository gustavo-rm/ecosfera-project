import { NOISE } from "./common";

/** Terrain, oceans, ice, lava, event effects and data layers in one pass. All vectors are in the planet's local space. */
export const SURFACE_FRAGMENT = /* glsl */ `
precision highp float;
varying vec4 vA; varying vec4 vB; varying vec4 vC; varying vec4 vD;
varying vec3 vDir; varying vec3 vGrad; varying vec3 vPos;
uniform vec3 uSunDir; uniform vec3 uCamPos; uniform vec3 uSkyColor; uniform vec3 uOceanShallow; uniform vec3 uOceanDeep; uniform vec3 uStarColor;
uniform float uTime; uniform float uExag; uniform float uSeed; uniform float uZoom; uniform float uAtmo; uniform float uHaze; uniform float uTermSoft;
uniform float uStarInt; uniform float uSurfaceHeat; uniform float uDesat; uniform float uSunDim; uniform float uLayerMode; uniform float uLayerOpacity; uniform float uHighlightPulse;
uniform sampler2D uLut;
uniform vec4 uRipple; uniform vec4 uShock; uniform vec4 uSelect;
${NOISE}
float ring(vec3 n, vec3 c, float radius, float width){ float a = acos(clamp(dot(n, c), -1.0, 1.0)); return smoothstep(width, 0.0, abs(a - radius)); }
void main(){
  vec3 n = normalize(vDir);
  float n1 = fbm(n * 6.0 + uSeed);
  float n2 = vnoise(n * 46.0 + uSeed);
  float n3 = uZoom > 0.01 ? fbm(n * 21.0 + uSeed * 2.0) : 0.5;
  float h = vA.x + (n1 - 0.5) * 0.016 + ((n3 - 0.5) * 0.014 + (n2 - 0.5) * 0.004) * uZoom - vD.x * 0.006;
  float land = smoothstep(-0.0012, 0.0012, h);
  float iceN = smoothstep(0.35, 0.65, vA.y + (n1 - 0.5) * 0.4);

  // ---- land
  vec3 nl = n - vGrad * uExag * 2.4;
  if (uZoom > 0.01) {
    // Procedural relief detail that grows as the camera gets closer: finite differences of the noise along the tangent plane.
    vec3 t1 = normalize(cross(n, vec3(0.0, 1.0, 0.001))), t2 = cross(n, t1);
    float e = 0.012;
    float ha = fbm((n + t1 * e) * 21.0 + uSeed * 2.0), hb = fbm((n + t2 * e) * 21.0 + uSeed * 2.0);
    nl -= (t1 * (ha - n3) + t2 * (hb - n3)) * (22.0 * uZoom) * (0.35 + 2.5 * clamp(vA.x, 0.0, 1.0));
  }
  nl = normalize(nl);
  vec3 col = vB.rgb * (0.80 + 0.40 * n1);
  col = mix(col, col * (0.62 + 0.7 * smoothstep(0.3, 0.7, n3)) * (0.8 + 0.4 * n2), 0.85 * uZoom);
  col = mix(col, col * vec3(0.62, 0.9, 0.62), clamp(vB.a, 0.0, 1.0) * uZoom * smoothstep(0.45, 0.75, n2) * 0.6);
  float gray = dot(col, vec3(0.3, 0.59, 0.11));
  col = mix(col, mix(vec3(gray), vec3(0.66, 0.54, 0.36), 0.4), clamp(vD.x, 0.0, 1.0) * 0.75);
  float crack = smoothstep(0.05, 0.0, abs(vnoise(n * 110.0 + uSeed) - 0.5)) * vD.x * (0.35 + 0.65 * uZoom);
  col *= 1.0 - 0.55 * crack;
  col = mix(col, vec3(0.10, 0.09, 0.085), clamp(vD.z, 0.0, 1.0) * 0.8);
  col = mix(col, vec3(0.93, 0.96, 1.0), iceN);
  float lavaAmt = max(vA.z, 0.0);
  float cr = 1.0 - abs(fbm(n * 9.0 + uSeed + vec3(0.0, uTime * 0.006, 0.0)) * 2.0 - 1.0);
  float cr2 = 1.0 - abs(vnoise(n * 31.0 + uSeed * 1.7) * 2.0 - 1.0);
  cr = pow(cr, 7.0) + 0.5 * pow(cr2, 9.0);
  float pool = smoothstep(0.55, 0.8, n1) * 0.5;
  float glow = clamp(lavaAmt * (0.18 + 1.3 * cr) * step(0.02, lavaAmt) + uSurfaceHeat * (0.05 + 1.25 * cr + pool * lavaAmt), 0.0, 1.3);
  col = mix(col, vec3(0.09, 0.055, 0.045), clamp(uSurfaceHeat * 0.92 + lavaAmt * 0.55, 0.0, 1.0));
  vec3 emissive = vec3(1.0, 0.30, 0.04) * glow + vec3(1.0, 0.75, 0.3) * pow(glow, 3.0) * 0.3;
  float flick = 0.7 + 0.3 * sin(uTime * 1.7 + n2 * 31.0);
  emissive += vec3(1.0, 0.42, 0.1) * vC.w * smoothstep(0.35, 0.8, n2 + vC.w * 0.5) * flick * land * 1.4;
  col = mix(col, vec3(0.09, 0.07, 0.06), vC.w * 0.6 * land);

  // ---- ocean
  float depth = clamp(-h * 5.0, 0.0, 1.0);
  vec3 oc = mix(uOceanShallow, uOceanDeep, smoothstep(0.0, 1.0, depth));
  oc = mix(oc, vec3(0.22, 0.47, 0.15), clamp(vC.z, 0.0, 1.0) * 0.7 * smoothstep(0.3, 0.7, n1 + vC.z * 0.3));
  oc = mix(oc, vec3(0.05, 0.065, 0.05), clamp(vD.z, 0.0, 1.0) * 0.8);
  vec3 wn = normalize(n + 0.014 * (vec3(vnoise(n * 130.0 + uTime * 0.16), vnoise(n * 130.0 + 31.0 + uTime * 0.13), vnoise(n * 130.0 + 57.0 - uTime * 0.11)) - 0.5));
  float foam = smoothstep(-0.0035, -0.0004, h) * (1.0 - land) * smoothstep(0.45, 0.75, vnoise(n * 90.0 + uTime * 0.07));
  oc = mix(oc, vec3(0.9, 0.95, 1.0), foam * (0.12 + 0.4 * uZoom));
  oc = mix(oc, uOceanShallow * 1.25 + 0.04, smoothstep(-0.02, 0.0, h) * 0.5);
  oc = mix(oc, vec3(0.9, 0.94, 0.98), iceN);

  vec3 base = mix(oc, col, land);
  vec3 nn = normalize(mix(wn, nl, land));
  vec3 v = normalize(uCamPos - vPos);
  float ndl = dot(nn, uSunDir);
  float day = smoothstep(-uTermSoft, uTermSoft, dot(n, uSunDir));
  vec3 light = uStarColor * uStarInt * uSunDim * (0.25 + 0.95 * max(ndl, 0.0)) * day + vec3(0.02) + uSkyColor * 0.07 * uAtmo * day;
  vec3 color = base * light;
  float water = (1.0 - land) * (1.0 - iceN);
  vec3 hv = normalize(v + uSunDir);
  color += uStarColor * uSunDim * pow(max(dot(wn, hv), 0.0), 190.0) * water * day * 0.7;
  float fres = pow(1.0 - max(dot(n, v), 0.0), 4.0);
  color += uSkyColor * fres * 0.3 * water * day;
  color += emissive * mix(1.0, 0.25, iceN);

  // ---- air between the camera and the surface
  float rim = pow(1.0 - max(dot(n, v), 0.0), 2.5);
  float dayAir = smoothstep(-0.25, 0.3, dot(n, uSunDir));
  color = mix(color, uSkyColor * (0.06 + 0.94 * dayAir) * uSunDim, clamp(uAtmo * (0.07 + 0.8 * rim) + uHaze * (0.30 + 0.5 * rim), 0.0, 0.93));
  color = mix(color, vec3(dot(color, vec3(0.3, 0.59, 0.11))), uDesat);

  // ---- data layer: literal data, flat lit so that light does not distort the reading
  if (uLayerMode > 0.5) {
    vec3 lc = uLayerMode < 1.5 ? texture2D(uLut, vec2(clamp(vC.x, 0.0, 1.0), 0.5)).rgb : vB.rgb;
    if (uLayerMode < 1.5 && vC.x < -0.5) lc = vec3(0.36, 0.38, 0.42);
    float shade = 0.78 + 0.22 * clamp(dot(nl, normalize(n + 0.7 * v)), 0.0, 1.0);
    vec3 dataCol = lc * shade * (1.0 - 0.4 * smoothstep(0.0035, 0.0, abs(h)));
    float hatch = step(0.5, fract((gl_FragCoord.x + gl_FragCoord.y) / 9.0));
    dataCol = mix(mix(vec3(0.20, 0.21, 0.24), vec3(0.36, 0.37, 0.40), hatch), dataCol, smoothstep(0.35, 0.65, vC.y));
    color = mix(color, dataCol, uLayerOpacity);
  }

  // ---- highlights and immediate feedback
  float hl = clamp(vD.w, 0.0, 1.0);
  float dash = step(0.5, fract((gl_FragCoord.x - gl_FragCoord.y) / 7.0));
  color = mix(color, vec3(1.0, 0.86, 0.25), smoothstep(0.12, 0.5, hl) * (0.28 + 0.14 * uHighlightPulse) + smoothstep(0.10, 0.16, hl) * smoothstep(0.24, 0.18, hl) * dash * 0.8);
  if (uRipple.w >= 0.0) color += vec3(0.75, 0.95, 1.0) * ring(n, uRipple.xyz, uRipple.w * 0.22, 0.012) * (1.0 - uRipple.w) * 0.9;
  if (uShock.w >= 0.0) color += vec3(1.0, 0.85, 0.6) * ring(n, uShock.xyz, uShock.w, 0.03) * 0.8;
  if (uSelect.w > 0.0) color = mix(color, vec3(1.0), ring(n, uSelect.xyz, uSelect.w, 0.0035) * 0.9);
  gl_FragColor = vec4(color, 1.0);
}`;
