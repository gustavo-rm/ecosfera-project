/* Shaders GLSL simples usados pela cena. Mantidos como strings isoladas para
 * facilitar leitura e reuso. */

/** Atmosfera: halo de Fresnel que brilha nas bordas e esquenta no lado do Sol. */
export const atmosphereVertexShader = /* glsl */ `
  varying vec3 vWorldNormal;
  varying vec3 vWorldPosition;

  void main() {
    vWorldNormal = normalize(mat3(modelMatrix) * normal);
    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vWorldPosition = worldPosition.xyz;
    gl_Position = projectionMatrix * viewMatrix * worldPosition;
  }
`;

export const atmosphereFragmentShader = /* glsl */ `
  uniform vec3 uColor;
  uniform vec3 uSunColor;
  uniform vec3 uSunDirection;
  uniform float uIntensity;
  uniform float uPower;
  uniform float uTime;

  varying vec3 vWorldNormal;
  varying vec3 vWorldPosition;

  void main() {
    vec3 viewDir = normalize(cameraPosition - vWorldPosition);
    vec3 normal = normalize(vWorldNormal);

    float fresnel = pow(1.0 - max(dot(viewDir, normal), 0.0), uPower);
    float sun = max(dot(normal, normalize(uSunDirection)), 0.0);

    vec3 color = mix(uColor, uSunColor, pow(sun, 3.0) * 0.7);
    float alpha = clamp(fresnel * uIntensity, 0.0, 1.0);

    gl_FragColor = vec4(color, alpha);
  }
`;

/** Campo de estrelas com cintilância independente por ponto. */
export const starfieldVertexShader = /* glsl */ `
  attribute float aSize;
  attribute float aPhase;
  attribute vec3 aColor;

  uniform float uTime;
  uniform float uPixelRatio;

  varying vec3 vColor;
  varying float vTwinkle;

  void main() {
    vColor = aColor;
    float wave = 0.5 + 0.5 * sin(uTime * 1.4 + aPhase);
    vTwinkle = 0.3 + 0.7 * wave;

    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mvPosition;
    gl_PointSize = aSize * uPixelRatio * (300.0 / -mvPosition.z);
  }
`;

export const starfieldFragmentShader = /* glsl */ `
  varying vec3 vColor;
  varying float vTwinkle;

  void main() {
    float d = length(gl_PointCoord - 0.5);
    float alpha = smoothstep(0.5, 0.0, d) * vTwinkle;
    if (alpha < 0.01) discard;
    gl_FragColor = vec4(vColor, alpha);
  }
`;
