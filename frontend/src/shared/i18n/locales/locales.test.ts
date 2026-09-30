import { describe, expect, it } from "vitest";

import en from "./en.json";
import es from "./es.json";

type Tree = { [key: string]: string | Tree };

/** Todas las claves hoja, con su ruta: "documents.upload.title". */
function keys(tree: Tree, prefix = ""): string[] {
  return Object.entries(tree).flatMap(([key, value]) =>
    typeof value === "string" ? [`${prefix}${key}`] : keys(value, `${prefix}${key}.`),
  );
}

describe("traducciones", () => {
  it("es y en tienen exactamente las mismas claves", () => {
    // Una clave que falta en un idioma se pinta en crudo ("documents.deleteTitle");
    // una en el bloque equivocado, también. Pasó en F13 con un texto insertado en
    // la sección de solicitudes en vez de la de documentos.
    const spanish = new Set(keys(es as Tree));
    const english = new Set(keys(en as Tree));

    expect([...spanish].filter((key) => !english.has(key))).toEqual([]);
    expect([...english].filter((key) => !spanish.has(key))).toEqual([]);
  });
});
