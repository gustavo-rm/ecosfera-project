import * as THREE from 'three'

/**
 * ESTRELA — mesma ideia do `planetKit.ts`, só que para o corpo central
 * do sistema: uma superfície procedural (grânulos quentes, manchas mais
 * frias) com escurecimento de limbo — a borda do disco fica mais escura
 * que o centro, como acontece de verdade no Sol.
 */
export function createStarMaterial(): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: {
      uCool: { value: new THREE.Color('#C96A1E') },
      uBase: { value: new THREE.Color('#FFC65C') },
      uHot: { value: new THREE.Color('#FFF3D6') },
      uTime: { value: 0 },
    },
    vertexShader: /* glsl */ `
      varying vec3 vObj; varying vec3 vN;
      void main() {
        vObj = position;
        vN = normalize(normalMatrix * normal);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      precision highp float;
      uniform vec3 uCool, uBase, uHot;
      uniform float uTime;
      varying vec3 vObj; varying vec3 vN;

      float hash(vec3 p){ p=fract(p*0.3183099+vec3(0.71,0.113,0.419)); p*=17.0; return fract(p.x*p.y*p.z*(p.x+p.y+p.z)); }
      float noise(vec3 x){
        vec3 i=floor(x), f=fract(x); f=f*f*(3.0-2.0*f);
        return mix(
          mix(mix(hash(i+vec3(0,0,0)),hash(i+vec3(1,0,0)),f.x), mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x), f.y),
          mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x), mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x), f.y), f.z);
      }
      float fbm(vec3 p){ float a=0.5,s=0.0; for(int i=0;i<4;i++){ s+=a*noise(p); p*=2.15; a*=0.5; } return s; }

      void main() {
        vec3 p = normalize(vObj);
        float n = fbm(p * 3.6 + vec3(uTime * 0.025));

        vec3 col = uCool;
        col = mix(col, uBase, step(0.42, n));
        col = mix(col, uHot,  step(0.63, n));

        float limb = pow(max(dot(normalize(vN), vec3(0.0, 0.0, 1.0)), 0.0), 0.35);
        col *= mix(0.5, 1.0, limb);

        gl_FragColor = vec4(col, 1.0);
      }
    `,
  })
}

/**
 * Aro de brilho aditivo (fresnel) — usado nas duas camadas de "corona"
 * ao redor da estrela. Mesma técnica de `createAtmosphere` do
 * planetKit.ts, só que parametrizável (raio/cor/intensidade diferentes
 * para cada camada).
 */
export function createGlow(radius: number, color: string, power: number, intensity: number): THREE.Mesh {
  return new THREE.Mesh(
    new THREE.SphereGeometry(radius, 48, 48),
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
          float rim = pow(1.0 - abs(dot(normalize(vN), vec3(0.0, 0.0, 1.0))), ${power.toFixed(1)});
          gl_FragColor = vec4(uColor, rim * ${intensity.toFixed(2)});
        }
      `,
    })
  )
}