const path = require('path'), fs = require('fs-extra');
const request = require('request'), htmlParser = require('node-html-parser');
var task = module.exports = {}, settings={};

var dataLocalJSON={
  info: {
    identify: '',
    name: '',
    shortname: '',
    year: '',
    language: {
      text: '',
      textdirection: "ltr",
      name: ''
    },
    version: 1,
    description: '',
    publisher: '',
    contributors: '',
    copyright: ''
  },
  note:{
  },
  language:{
    book:"Book",
    chapter:"Chapter",
    verse:"Verse"
  },
  digit:["0","1","2","3","4","5","6","7","8","9"],
  testament:{
    1: {
      info: {
        name: "Old Testament",
        shortname: "OT",
        desc: ""
      }
    },
    2: {
      info: {
        name: "New Testament",
        shortname: "NT",
        desc: ""
      }
    }
  },
  story: {
  },
  book: {
  }
},
dumpBookName=[],
initial = function(){
  return new Promise(function(resolve, reject) {
    readLocalJSON().then(function(){
      if (settings.apiData){
        requestBookName().then(function(){
          asyncEach().then(function(e){
            resolve(e);
          },function(e){
            reject(e);
          });
        },function(e){
          reject(e);
        });
      } else {
        // resolve(dataLocalJSON);
        parseFinalJSON(dataLocalJSON).then(function(e){
          resolve(e);
        },function(e){
          reject(e);
        });
      }
    },function(e){
      reject(e);
    });
  });
},
asyncEach = function(){
  return new Promise(function(resolve, reject) {
    asyncTask(resolve, reject).then(function(e){
      resolve(e);
    },function(e){
      reject(e);
    });
  });
},
asyncTask = async function(resolve, reject){
  try {
    await requestChapter();
    if (settings.apiURLChapter) {
      return asyncEach();
    } else {
      resolve(dataLocalJSON);
    }
  }
  catch (e) {
    reject(e);
  }
},
requestBookName = function(){
  return new Promise(function(resolve, reject) {
    request(settings.apiURLBookName, { json: true }, (e, res, body) => {
      if (e) {
        reject(e);
      } else {
        // console.log(body.items);
        // dataLocalJSON.dump_bookname = body.items;
        dumpBookName = body.items;
        resolve()
      }
    });
  });
},
requestBookId = '',
requestChapter = function(){
  return new Promise(function(resolve, reject) {
    request(settings.apiURLChapter, { json: true }, (e, res, body) => {
      if (e) {
        reject(e);
      } else {
        const root = htmlParser.parse(body);
        const rootChapter = root.querySelector('div.chapter');
        const currentBookChapter = rootChapter.attributes['data-usfm'].split('.');
        var bookId = 1;
        var bookShortName = currentBookChapter[0];
        var chapterId = currentBookChapter[1];

        var bookInfo = dumpBookName.find(element => element.usfm === bookShortName);
        var index = dumpBookName.indexOf(bookInfo);
        if (index > -1) {
          bookId =  index + bookId;
        } else {
          return reject('No book info found');
        }

        var hasNext = root.querySelector('a.bible-nav-button.nav-right');
        if (hasNext) {
          if (settings.apiDataOnlyOne){
            settings.apiURLChapter = null;
          } else {
            settings.apiURLChapter = settings.apiDomain.replace('*',hasNext.attributes.href);
          }
        } else {
          settings.apiURLChapter = null;
        }

        if (!dataLocalJSON.book.hasOwnProperty(bookId)) {
          dataLocalJSON.book[bookId]={
            info:{
              name: bookInfo.human,
              shortname: bookShortName,
              abbr:[],
              desc: ""
            },
            topic:[],
            chapter:{}
          };
        }
        dataLocalJSON.book[bookId].chapter[chapterId]={
          verse:{}
        };
        if (requestBookId == bookId) {
          settings.message.chapter(chapterId);
        } else {
          settings.message.book(bookId,chapterId);
        }
        requestBookId = bookId;

        var verseTitle ={value:'',add:false};
        rootChapter.childNodes.forEach(chapterNode => {
          if (chapterNode.childNodes.length > 0) {
            chapterNode.childNodes.forEach(verseNode => {

             if (verseNode  && verseNode.attributes) {
                var verseInfo = verseNode.attributes['data-usfm'];
                if (verseInfo) {
                  var verseIdArray = verseInfo.split('.');
                  var verseId = verseIdArray[2].split('+')[0];
                  var verseMerge ='';
                  var verseReference ='';

                  if (verseIdArray.length > 4) {
                    // NOTE verse merge 'REV.22.17+REV.22.18'
                    verseMerge = verseIdArray[4];
                  }

                  var verseNote = verseNode.querySelector('.note.x');
                  if (verseNote){
                    var verseNoteBody = verseNote.querySelector('.body');
                    if (verseNoteBody){
                      // NOTE has reference
                      verseReference = verseNoteBody.rawText.trim();
                      // console.log('reference ->',verseId,verseReference);
                    }
                  }
                  // var verseContent = verseNode.querySelector('.content');
                  // var verseText = verseContent.text.trim();

                  var verseContent = verseNode.querySelectorAll('.content').map(e=>e.text);
                  var verseText = verseContent.join(' ').replace(/\s\s+/g, ' ').trim();
                  var verseTitleValue =verseTitle.add?verseTitle.value:'';

                  if (verseText){
                    // console.log('verse ->',verseId,verseText);
                    if (!dataLocalJSON.book[bookId].chapter[chapterId].verse.hasOwnProperty(verseId)){
                      // NOTE insert new verse
                      dataLocalJSON.book[bookId].chapter[chapterId].verse[verseId]={
                        text:verseText,
                        title:verseTitleValue,
                        ref:verseReference,
                        merge:verseMerge
                      }
                    } else {
                      // NOTE update verse, because already exists
                      // console.log('verse already there ->',verseId,verseText);
                      var verseToJoin = dataLocalJSON.book[bookId].chapter[chapterId].verse[verseId];
                      // var verseTextJoin = verseToJoin.text+'\n '+verseText;
                      dataLocalJSON.book[bookId].chapter[chapterId].verse[verseId].text=verseToJoin.text+'\n '+verseText;
                      dataLocalJSON.book[bookId].chapter[chapterId].verse[verseId].title=verseTitleValue;
                      dataLocalJSON.book[bookId].chapter[chapterId].verse[verseId].ref=(verseToJoin.ref+' '+verseReference).trim();
                      dataLocalJSON.book[bookId].chapter[chapterId].verse[verseId].merge=verseMerge;
                    }
                    verseTitle.add=false;
                  }

                } else if (verseNode.attributes.class == 'heading'){
                  verseTitle.value = verseNode.rawText.trim();
                  verseTitle.add = true;
                  // console.log('heading ->',verseTitle);
                }

              }
            });
          }
        });
        // console.log(rootChapter.childNodes[0]);
        resolve();
      }
    });
  });
},

stringifyJSON = function(data) {
  if (settings.args.length > 2) {
    return JSON.stringify(data, null, 2);
  } else {
    return JSON.stringify(data);
  }
},
readLocalJSON = function(){
  // dataLocalJSON dataLocalJSON
  return new Promise(function(resolve, reject) {
    if (!settings.bookIdentify) return reject(`...\x1b[35m${settings.bookIdentify}\x1b[0m!`);
    var sourceFile = path.resolve(settings.rootDirectory,settings.task.wbc.dirname,settings.task.json.extension.replace('*',settings.bookIdentify));
    fs.readFile(sourceFile, function(e, data) {
      if (e) {
        if (e.code == 'ENOENT') {
          settings.message.standard(`new \x1b[35mJSON\x1b[0m to be created!`);
        }
        resolve();
      } else {
        try {
          dataLocalJSON=JSON.parse(data);
          return resolve();
        } catch (e) {
          return reject(e);
        }
      }
    });
  })
},
writeLocalJSON = function(data) {
  return new Promise((resolve, reject) => {
    var bookSourceJSONName = settings.task.json.extension.replace('*',settings.bookIdentify);
    var bookSourceJSON = path.resolve(settings.rootDirectory,settings.task.wbc.dirname,bookSourceJSONName);
    fs.writeFile(bookSourceJSON, stringifyJSON(data),'utf8',function(error){
      if (error) {
        reject(error);
      } else {
        console.log(`\n...updated local\x1b[32m ${bookSourceJSONName}\x1b[0m!`);
        resolve();
      }
    });
  });
};
writeFinalJSON = function(data) {
  return new Promise((resolve, reject) => {
    var bookSourceJSONName = settings.task.json.extension.replace('*',settings.bookIdentify);
    var bookSourceJSON = path.resolve(settings.rootDirectory,settings.task.json.dirname,bookSourceJSONName);
    fs.writeFile(bookSourceJSON, stringifyJSON(data),'utf8',function(error){
      if (error) {
        reject(error);
      } else {
        console.log(`\n...updated final\x1b[32m ${bookSourceJSONName}\x1b[0m!`);
        resolve();
      }
    });
  });
},
writeJSON = function(data) {
  return new Promise((resolve, reject) => {
    if (settings.apiData){
      writeLocalJSON(data).then(function(){
        resolve();
      },function(e){
        reject(e);
      });
    } else if (dataLocalJSON.info.identify && dataLocalJSON.info.name && dataLocalJSON.info.shortname && dataLocalJSON.info.year){
      writeFinalJSON(data).then(function(){
        resolve(data);
      },function(e){
        reject(e);
      });
    } else {
      settings.message.unknown('Required: info > identify,name,shortname,year for final output!');
      if (typeof data === 'string'){
        settings.message.unknown(data);
        // console.log(data);
      }
      resolve();
    }
  });
},
parseFinalJSON = function(data){
  return new Promise(function(resolve, reject) {
    try {
      var result={
        info:data.info,
        note:{},
        digit:data.digit,
        language:data.language,
        testament:data.testament,
        story:data.story,
        book:parseBook(data.book)
      };
      return resolve(result);
    } catch (e) {
      return reject(e);
    }
  });
},
parseBook = function(data){
  var result={};
  for (const bId in data) {
    if (data.hasOwnProperty(bId)) {
      const book = data[bId];
      if (book.hasOwnProperty('chapter')){
        result[bId]={
          info:parseBookInfo(book.info),
          chapter:{}
        };
        for (const cId in book.chapter) {
          if (book.chapter.hasOwnProperty(cId)) {
            const chapter = book.chapter[cId];
            if (chapter.hasOwnProperty('verse')){
              result[bId].chapter[cId]={
                verse:{}
              };
              for (const vId in chapter.verse) {
                if (chapter.verse.hasOwnProperty(vId)) {
                  var newVerse={};
                  const verse = chapter.verse[vId];
                  if (verse.text && verse.text !="") {
                    newVerse.text=verse.text;
                  } else {
                    console.log('verse has no text',bId,cId,vId);
                  }
                  if (verse.title && verse.title !="") newVerse.title=verse.title;
                  if (verse.merge && verse.merge !="") newVerse.merge=verse.merge;
                  if (verse.ref && verse.ref !="") newVerse.ref=verse.ref;
                  result[bId].chapter[cId].verse[vId]=newVerse;
                }
              }
            } else {
              console.log('has no verse');
            }
          }
        }
      } else {
        console.log('has no chapter');
      }
    }
  }
  // data.forEach(function(bid){
  //   console.log('bookid',bid);
  // });
  return result;
},
parseBookInfo = function(result){
  if (result.name){
    // result.name = result.name.split(' ').map( w =>  w.substring(0,1).toUpperCase()+ w.substring(1)).join(' ');
    result.name = result.name.toLowerCase().split(' ').map(value => value.charAt(0).toUpperCase() + value.substring(1)).join(' ');
    // result.apple="what";
  }
  return result;
};
// https://www.bible.com/json/bible/languages?filter=
// https://www.bible.com/json/bible/books/348?filter=
// https://www.bible.com/json/bible/books/348/GEN/chapters

// https://www.bible.com/bible/348/REV.22.JCLB
// https://www.bible.com/bible/348/GEN.1.JCLB
// GEN.1.6+GEN.1.7

// node bible wbc 348
// node bible wbc bible/348/GEN.1.JCLB true
// node bible wbc /bible/348/GEN.1.JCLB true
task.main = function(args) {
  settings = args;
  settings.apiDomain = '*/moc.elbib.www//:sptth'.split('').reverse().join('');

  settings.apiDataOnlyOne=false;
  settings.apiData = false;
  settings.apiURLChapter = null;
  settings.apiURLBookName = null;
  var apiPathBookName = 'json/bible/books/*';

  if (/\//g.test(settings.bookIdentify)){
    settings.apiData = true;
    var tmp = settings.bookIdentify.split('/');
    if (tmp[0]){
      // NOTE -> bible/348/GEN.1.JCLB
      settings.bookIdentify = tmp[1];
    } else {
      // NOTE -> /bible/348/GEN.1.JCLB
      settings.bookIdentify = tmp[2];
      settings.apiDataOnlyOne = true;
      tmp.shift();
    }
    settings.apiURLChapter = settings.apiDomain.replace('*',tmp.join('/'));
    settings.apiURLBookName = settings.apiDomain.replace('*',apiPathBookName.replace('*',settings.bookIdentify));
  }

  return new Promise(function(resolve, reject) {
    initial().then(function(result){
      writeJSON(result).then(function(r){
        resolve(r);
      },function(e){
        reject(e);
      });
    },function(e){
      reject(e);
    });
  });
};