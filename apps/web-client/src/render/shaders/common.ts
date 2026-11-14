/** GLSL shared by the planet shaders. GLSL on WebGLRenderer (WebGL 2): see docs/frontend/adr/0001. */
export const NOISE = /* glsl */ `
float hash31(vec3 p){ p = fract(p * 0.3183099 + vec3(0.71, 0.113, 0.419)); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float vnoise(vec3 x){
  vec3 i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(hash31(i), hash31(i + vec3(1,0,0)), f.x), mix(hash31(i + vec3(0,1,0)), hash31(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(hash31(i + vec3(0,0,1)), hash31(i + vec3(1,0,1)), f.x), mix(hash31(i + vec3(0,1,1)), hash31(i + vec3(1,1,1)), f.x), f.y), f.z);
}
float fbm(vec3 p){ float a = 0.5, s = 0.0; for (int i = 0; i < OCTAVES; i++) { s += a * vnoise(p); p = p * 2.03 + vec3(17.1); a *= 0.5; } return s / (1.0 - pow(0.5, float(OCTAVES))); }
`;

export const CELL_VERTEX = /* glsl */ `
attribute vec4 aA0; attribute vec4 aB0; attribute vec4 aC0; attribute vec4 aD0;
attribute vec4 aA1; attribute vec4 aB1; attribute vec4 aC1; attribute vec4 aD1;
attribute vec3 aGrad;
uniform float uBlend; uniform float uExag; uniform float uShell;
varying vec4 vA; varying vec4 vB; varying vec4 vC; varying vec4 vD;
varying vec3 vDir; varying vec3 vGrad; varying vec3 vPos;
void main(){
  vA = mix(aA0, aA1, uBlend); vB = mix(aB0, aB1, uBlend); vC = mix(aC0, aC1, uBlend); vD = mix(aD0, aD1, uBlend);
  vDir = normalize(position); vGrad = aGrad;
  // uShell = 0: surface displaced by the (exaggerated) relief. uShell > 0: a smooth shell at that altitude (clouds).
  float h = max(vA.x, 0.0);
  vec3 p = vDir * (uShell > 0.0 ? 1.0 + uShell : 1.0 + h * uExag);
  vPos = p;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
}`;
