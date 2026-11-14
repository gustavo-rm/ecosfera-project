/**
 * Cell ordering of the geodesic mesh. THIS IS THE ONLY MODULE THAT DEFINES THE ORDER OF CELLS.
 *
 * TODO(contract): the order of cells will be part of the future data contract with the engine
 * (Evolution Engine spec §6.2, DEC-04). The spec file is not in the repository, so the exact vertex
 * order of the server mesh could not be confirmed. If the server uses a different order, change only
 * this module (or add a permutation table here). Nothing else in the client may assume an order.
 *
 * Convention used here (deterministic):
 *  - Level 0: the 12 vertices of an icosahedron, in the order of BASE_VERTICES below.
 *  - Level L+1: all vertices of level L keep their index (prefix property). New vertices are appended
 *    in the order in which edge midpoints are first met while walking the triangles of level L in
 *    order, edges (a,b), (b,c), (c,a).
 *  - Count: 10 * 4^L + 2 (level 5 = 10 242 cells, 12 of them pentagonal).
 */
const T = (1 + Math.sqrt(5)) / 2;
const BASE_VERTICES: ReadonlyArray<readonly [number, number, number]> = [
  [-1, T, 0], [1, T, 0], [-1, -T, 0], [1, -T, 0],
  [0, -1, T], [0, 1, T], [0, -1, -T], [0, 1, -T],
  [T, 0, -1], [T, 0, 1], [-T, 0, -1], [-T, 0, 1],
];
const BASE_FACES: ReadonlyArray<readonly [number, number, number]> = [
  [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
  [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
  [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
  [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
];

export interface OrderedIcosphere {
  level: number;
  count: number;
  /** Unit vectors, xyz per cell. */
  centers: Float32Array;
  /** Triangle list of the dual render mesh (cells are vertices). */
  indices: Uint32Array;
  /** For each cell, the two cells of the previous level whose edge midpoint created it (itself twice if older). */
  edgeParents: Int32Array;
  /** Level at which each cell first appeared. */
  birthLevel: Uint8Array;
}

export const cellCountForLevel = (level: number) => 10 * 4 ** level + 2;

export function buildOrderedIcosphere(level: number): OrderedIcosphere {
  const count = cellCountForLevel(level);
  const centers = new Float32Array(count * 3);
  const edgeParents = new Int32Array(count * 2);
  const birthLevel = new Uint8Array(count);
  let n = 0;
  const push = (x: number, y: number, z: number, a: number, b: number, lvl: number) => {
    const l = Math.hypot(x, y, z);
    centers[n * 3] = x / l; centers[n * 3 + 1] = y / l; centers[n * 3 + 2] = z / l;
    edgeParents[n * 2] = a < 0 ? n : a; edgeParents[n * 2 + 1] = b < 0 ? n : b;
    birthLevel[n] = lvl;
    return n++;
  };
  for (const v of BASE_VERTICES) push(v[0], v[1], v[2], -1, -1, 0);
  let faces = new Uint32Array(BASE_FACES.flat());
  for (let l = 1; l <= level; l++) {
    const cache = new Map<number, number>();
    const stride = cellCountForLevel(l);
    const mid = (a: number, b: number) => {
      const key = a < b ? a * stride + b : b * stride + a;
      let m = cache.get(key);
      if (m === undefined) {
        m = push(
          centers[a * 3] + centers[b * 3], centers[a * 3 + 1] + centers[b * 3 + 1], centers[a * 3 + 2] + centers[b * 3 + 2],
          Math.min(a, b), Math.max(a, b), l,
        );
        cache.set(key, m);
      }
      return m;
    };
    const next = new Uint32Array(faces.length * 4);
    for (let f = 0, o = 0; f < faces.length; f += 3) {
      const a = faces[f], b = faces[f + 1], c = faces[f + 2];
      const ab = mid(a, b), bc = mid(b, c), ca = mid(c, a);
      next.set([a, ab, ca, b, bc, ab, c, ca, bc, ab, bc, ca], o);
      o += 12;
    }
    faces = next;
  }
  return { level, count, centers, indices: faces, edgeParents, birthLevel };
}
