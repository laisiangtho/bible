// import { JSDOM } from "jsdom";
// import * as csv from "csv";
import { seek } from "lethil";

import { env } from "../anchor/index.js";
export { env } from "../anchor/index.js";

/**
 * Read JSON file
 */
export const readJSON = seek.readJSON;
/**
 * Write JSON file
 */
export const writeJSON = seek.writeJSON;

/**
 * Remove double spaces, trim
 * “ ”
 * @param {string} e
 * @returns
 */
export function textFormat(e) {
  // return e.replace(/“/g, "'").replace(/”/g, "'");
  return e.replace(/\s\s+/g, " ").trim();
}

/**
 * GEN.2.1
 * @param {string} e
 * @returns {string}
 */
export function getBookIdByName(e) {
  let name = e[0].toUpperCase() + e.slice(1).toLowerCase();
  let book = env.category.name.book;

  let bk = Object.keys(book)
    .map((k) => {
      let o = book[k];
      if (o.info.abbr[0] == name) {
        return k;
      }
    })
    .filter((x) => x);
  if (bk[0]) {
    return bk[0];
  }
  return "0";
}

/**
 * @type {env.TypeOfTestament}
 */
export const _testament = {
  1: {
    info: {
      name: "Thuciam Lui",
      shortname: "TL",
    },
    other: {},
  },
  2: {
    info: {
      name: "Thuciam Thak",
      shortname: "TT",
    },
    other: {},
  },
};

/**
 * @type {env.TypeOfStory}
 */
export const _story = {
  1: {
    1: {
      1: {
        text: "Van leh lei, leh mihing a kipiansakna",
        ref: "Gen.1.1,Gen.2.25",
      },
    },
    3: {
      1: {
        text: "Mawhna leh gimna a kipatna",
        ref: "Gen.3.1",
      },
    },
    4: {
      1: {
        text: "Adam pan Noah thu",
        ref: "Gen.4.1,Gen.5.32",
      },
    },
  },
};

/**
 * @type {env.TypeOfBibleBook}
 */
export const _book = {
  1: {
    info: {
      name: "Piancilna",
      shortname: "Pian",
      abbr: [],
      desc: "Piancilna cih kammal pen ‘kipatna’ a cihna ahi hi. Hih laibu sungah van leh lei a kipiansakna, mihing hong kipat khiatna, leitungah mawhna leh gimna hong kipatna, leh Pasian in mihingte tungah na hong sepna ziate kigen hi. Piancilna laibu a thu khen nih kisuah thei hi. A lian 1—11: Leitung a kipiansakna leh mihing a piang masate thu ahi hi. Hih sung tengah Adam leh Eve, Kain leh Abel, Noah leh tuiciin, leh Babel Tausangpi thute a om hi. A lian 12—50: Israel mite' pianna pupi masate' thu a om hi. A masa pen Abraham hi a, Pasian a upna leh a thu a man'na hangin a minthang khat ahi hi. Tua ciangin ama tapa Isaac' thu in hong zom a, tua ciangin a tupa Jakob (Israel zong a kicipa) in hong zom a, tua ciangin Jakob' ta sawmlenihte in hong zom a, hih sawmlenihte pen Israel minam sawmlenihte' hong piankhiatna ahi uh hi. Hih sung tengah, Jakob' ta sawmlenihte' lakah Josef a kicipa' thu leh a dangte a innkuan ciat uh tawh Egypt gamah a teng dingin a paina thu kilim gen pha diak hi. Hih laibu sungah mihingte' thu kigen a, tua sung panin Pasian' sepna bulphuhin kigen hi. Pasian in van leh lei a piansakna thu tawh na kipan a, Pasian in ama mite a lunghihmawhpih tawntungna ding kamciamna tawh a thu na khum hi. Hih laibu sung khempeuhah Pasian a semkhia bulpipa ahihna thu na gen a, amah in a khial mite tungah thu khenin gim a piakna, a mite makaihin a huhna, leh a mailam nuntakna ding zia uh a bawlsakna thute kigelh hi. Hih laibu pen mihingte in upna a neihna thu ciamtehna ding leh tua upna a letkip paisuak zawhna ding uh deihna tawh a kigelh ahi hi.",
    },
    topic: {},
    chapter: {
      1: {
        verse: {
          1: {
            text: "A kipat cilin Pasian in vantung leh leitung a piangsak hi.",
            title: "Leitung leh Mihing Pian'sakna",
          },
        },
      },
    },
  },
};

/**
 * @type {env.TypeOfBible}
 */
export const _bible = {
  info: {
    identify: "tedim1932",
    name: "Lai Siangtho",
    shortname: "Tedim",
    year: "1932",
    language: {
      text: "Zolai/Tedim",
      textdirection: "ltr",
      name: "zo",
    },
    version: 0,
    description: "",
    publisher: "",
    contributors: "",
    copyright: "",
  },
  note: {},
  language: {
    chapter: "Alian",
    verse: "Aneu",
  },
  digit: ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
  testament: {
    1: {
      info: {
        name: "Thuciam Lui",
        shortname: "TL",
      },
      other: {},
    },
    2: {
      info: {
        name: "Thuciam Thak",
        shortname: "TT",
      },
      other: {},
    },
  },
  story: {
    1: {
      1: {
        1: {
          title: "?",
          text: "...",
          other: "?",
        },
      },
    },
  },
  book: {
    1: {
      info: {
        name: "Piancilna",
        shortname: "Pian",
        abbr: [],
        desc: "",
      },
      topic: [
        {
          text: "Van leh lei, leh mihing a kipiansakna",
          ref: "Gen.1.1,Gen.2.25",
        },
      ],
      chapter: {
        1: {
          verse: {
            1: {
              text: "?",
              title: "?",
              heading: "?",
              ref: "?",
              merge: "?",
            },
          },
        },
        2: {
          verse: {},
        },
      },
    },
  },
};
