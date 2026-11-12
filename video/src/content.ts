/**
 * Todo lo que se lee en el vídeo. Para cambiar textos, imágenes o capturas basta
 * con editar este fichero (las capturas viven en public/shots/).
 */
export const CONTENT = {
  appName: "Applications Tracker",
  logo: "logo.png",

  intro: {
    tagline: "Una nueva forma de buscar trabajo",
  },

  presentation: {
    problem: "Decenas de ofertas, hojas de cálculo y correos perdidos.",
    solution: "Todo tu proceso de selección, en un solo lugar.",
    shot: "shots/13-dashboard-oscuro.png",
    url: "applications-tracker / dashboard",
  },

  features: [
    {
      chip: "01 · Tablero",
      title: "Arrastra y suelta",
      sub: "Mueve cada candidatura por su ciclo de vida.",
      caption: "Cada columna solo acepta los estados permitidos.",
      shot: "shots/14-tablero-oscuro.png",
    },
    {
      chip: "02 · Historial",
      title: "Cada paso, registrado",
      sub: "Estados, entrevistas y recordatorios de cada solicitud.",
      caption: "Y puedes deshacer el último cambio.",
      shot: "shots/15-detalle-oscuro.png",
    },
    {
      chip: "03 · CV con IA",
      title: "Un CV para cada oferta",
      sub: "La IA propone; tú revisas cada cambio.",
      caption: "Mide cuánto de lo que pide la oferta aparece en tu CV.",
      shot: "shots/16-cv-con-ia-oscuro.png",
      metricLabel: "Encaje con la oferta",
      metricFrom: 92,
      metricTo: 100,
    },
    {
      chip: "04 · Carta con IA",
      title: "Cartas que se sostienen",
      sub: "Cada párrafo, apoyado en tu perfil.",
      caption: "Sin inventar: nada llega al PDF sin que lo apruebes.",
      shot: "shots/07-carta-con-ia.png",
    },
    {
      chip: "05 · Calendario",
      title: "Nada se escapa",
      sub: "Entrevistas y recordatorios, en tu zona horaria.",
      caption: "Añádelos a Google Calendar con un clic.",
      shot: "shots/08b-calendario-semana.png",
    },
  ],

  result: {
    stats: [
      { value: 14, suffix: "", label: "candidaturas en marcha" },
      { value: 57, suffix: " %", label: "tasa de respuesta" },
      { value: 3, suffix: "", label: "entrevistas esta semana" },
    ],
    phones: [
      "shots/17-movil-dashboard.png",
      "shots/19-movil-detalle.png",
      "shots/20-movil-calendario.png",
    ],
    heading: "Tu búsqueda, bajo control.",
    message: "Menos caos.\nMás entrevistas.",
  },

  outro: {
    phrase: "Menos caos. Más entrevistas.",
    sub: "Tu búsqueda de empleo, bajo control.",
  },
};
