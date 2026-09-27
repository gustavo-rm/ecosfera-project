export type Task = { 
  title: string; 
  tag: string; 
  due: string; 
  done: boolean; 
}

export interface SimState {
  rotating: boolean;
  speed: number;
  targetRadius: number;
}
