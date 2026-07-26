import { Bloom, EffectComposer, Vignette } from '@react-three/postprocessing';

/** Bloom seletivo por luminância — só a atmosfera, a vida e os brilhos passam
 *  do limiar. Vignette adiciona profundidade sem escurecer o card. */
export function PostProcessing({ intensity }: { intensity: number }) {
  return (
    <EffectComposer multisampling={2}>
      <Bloom
        mipmapBlur
        intensity={intensity}
        luminanceThreshold={0.35}
        luminanceSmoothing={0.25}
        radius={0.72}
      />
      <Vignette offset={0.3} darkness={0.68} eskil={false} />
    </EffectComposer>
  );
}
