import { common } from "./pt-BR/common";
import { game } from "./pt-BR/game";
import { pedagogy } from "./pt-BR/pedagogy";
import { planet } from "./pt-BR/planet";
import { data } from "./pt-BR/data";
import { teacher } from "./pt-BR/teacher";
import { lab } from "./pt-BR/lab";

/** pt-BR is the base locale (RNF-026). A key "_" holds the text of its parent node. */
export const ptBR = { ...common, ...planet, ...game, ...data, ...teacher, ...lab, ped: pedagogy };
