import * as THREE from 'three'

/**
 * PLANETA — material e atmosfera compartilhados entre qualquer cena que
 * precise de um "planeta procedural": o do hero e o da seção final usam
 * exatamente esta fábrica, cada um com sua própria paleta e `seed`.
 *
 * O terreno é gerado por ruído (fbm) inteiramente na GPU e pintado em
 * FAIXAS CHAPADAS (`step`, não gradiente) — daí o visual "sólido" em vez
 * de foto-realista. `seed` desloca o ponto de amostragem do ruído, então
 * dois planetas com a mesma paleta ainda têm continentes diferentes.
 */

export type PlanetColorOptions = {
  ocean?: string
  shelf?: string
  coast?: string
  land?: string
  forest?: string
  rock?: string
  ice?: string
  rim?: string
  seed?: number
  lightDir?: THREE.Vector3
}

const VERTEX_SHADER = /* glsl */ `
  varying vec3 vObj;
  varying vec3 vN;
  void main() {
    vObj = position;
    vN = normalize(normalMatrix * normal);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`

const FRAGMENT_SHADER = /* glsl */ `
  precision highp float;
  uniform vec3 uOcean, uShelf, uCoast, uLand, uForest, uRock, uIce, uRim, uLightDir;
  uniform float uSeed;
  varying vec3 vObj;
  varying vec3 vN;

  float hash(vec3 p) {
    p = fract(p * 0.3183099 + vec3(0.71, 0.113, 0.419));
    p *= 17.0;
    return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
  }
  float noise(vec3 x) {
    vec3 i = floor(x), f = fract(x);
    f = f * f * (3.0 - 2.0 * f);
    return mix(
      mix(mix(hash(i + vec3(0,0,0)), hash(i + vec3(1,0,0)), f.x),
          mix(hash(i + vec3(0,1,0)), hash(i + vec3(1,1,0)), f.x), f.y),
      mix(mix(hash(i + vec3(0,0,1)), hash(i + vec3(1,0,1)), f.x),
          mix(hash(i + vec3(0,1,1)), hash(i + vec3(1,1,1)), f.x), f.y), f.z);
  }
  float fbm(vec3 p) {
    float a = 0.5, s = 0.0;
    for (int i = 0; i < 5; i++) { s += a * noise(p); p *= 2.03; a *= 0.5; }
    return s;
  }

  void main() {
    vec3 p = normalize(vObj);
    float h = fbm(p * 2.3 + vec3(uSeed));
    h += 0.30 * smoothstep(0.72, 1.0, abs(p.y)); // calotas polares

    // faixas de cor CHAPADAS (step, não gradiente)
    vec3 col = uOcean;
    col = mix(col, uShelf,  step(0.455, h));
    col = mix(col, uCoast,  step(0.505, h));
    col = mix(col, uLand,   step(0.525, h));
    col = mix(col, uForest, step(0.590, h));
    col = mix(col, uRock,   step(0.675, h));
    col = mix(col, uIce,    step(0.760, h));

    // luz em 3 degraus — mantém o aspecto "sólido"
    float d = dot(normalize(vN), normalize(uLightDir));
    float lit = 0.22 + 0.34 * step(-0.05, d) + 0.44 * step(0.35, d);
    col *= lit;

    float rim = pow(1.0 - max(dot(normalize(vN), vec3(0.0, 0.0, 1.0)), 0.0), 3.5);
    col += uRim * rim * 0.45;

    gl_FragColor = vec4(col, 1.0);
  }
`

export function createPlanetMaterial(opts: PlanetColorOptions = {}): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: {
      uOcean: { value: new THREE.Color(opts.ocean ?? '#123A6B') },
      uShelf: { value: new THREE.Color(opts.shelf ?? '#1D6FA8') },
      uCoast: { value: new THREE.Color(opts.coast ?? '#C7B98A') },
      uLand: { value: new THREE.Color(opts.land ?? '#2F7D4E') },
      uForest: { value: new THREE.Color(opts.forest ?? '#1F5A38') },
      uRock: { value: new THREE.Color(opts.rock ?? '#5B6674') },
      uIce: { value: new THREE.Color(opts.ice ?? '#E6F0FA') },
      uRim: { value: new THREE.Color(opts.rim ?? '#3FA9FF') },
      uSeed: { value: opts.seed ?? 0 },
      uLightDir: {
        value: (opts.lightDir ?? new THREE.Vector3(-0.45, 0.55, 0.7)).clone().normalize(),
      },
    },
    vertexShader: VERTEX_SHADER,
    fragmentShader: FRAGMENT_SHADER,
  })
}

/** Atmosfera fina — um aro de luz na borda (Fresnel), não névoa espalhada. */
export function createAtmosphere(radius: number, color: string): THREE.Mesh {
  return new THREE.Mesh(
    new THREE.SphereGeometry(radius, 64, 64),
    new THREE.ShaderMaterial({
      transparent: true,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      uniforms: { uColor: { value: new THREE.Color(color) } },
      vertexShader: /* glsl */ `
        varying vec3 vN;
        void main() {
          vN = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: /* glsl */ `
        uniform vec3 uColor;
        varying vec3 vN;
        void main() {
          float rim = pow(1.0 - abs(dot(normalize(vN), vec3(0.0, 0.0, 1.0))), 5.0);
          gl_FragColor = vec4(uColor, rim * 0.8);
        }
      `,
    })
  )
}
