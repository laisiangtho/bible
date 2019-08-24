const path = require('path');
// const fs = require('fs-extra');
const request = require('request');
const htmlParser = require('node-html-parser');
// usr, param
var param = {};
var dataBookName=[];
var dataBibleJSON={};
var requestBookId = '';

// https://www.bible.com/json/bible/languages?filter=
// https://www.bible.com/json/bible/books/348?filter=
// https://www.bible.com/json/bible/books/348/GEN/chapters

// https://www.bible.com/bible/348/REV.22.JCLB
// https://www.bible.com/bible/348/GEN.1.JCLB
// GEN.1.6+GEN.1.7

// node bible wbc 348
// node bible wbc bible/348/GEN.1.JCLB --indentation
// node bible wbc /bible/348/GEN.1.JCLB --indentation


function initial(){
  return new Promise(function(resolve, reject) {
    readLocalJSON().then(function(data){
      dataBibleJSON=data;
      if (param.apiData){
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
        // resolve(dataBibleJSON);
        parseFinalJSON(dataBibleJSON).then(function(e){
          resolve(e);
        },function(e){
          reject(e);
        });
      }
    },function(e){
      reject(e);
    });
  });
};

function asyncEach(){
  return new Promise(function(resolve, reject) {
    asyncTask(resolve, reject).then(function(e){
      resolve(e);
    },function(e){
      reject(e);
    });
  });
};

async function asyncTask(resolve, reject){
  try {
    await requestChapter();
    if (param.apiURLChapter) {
      return asyncEach();
    } else {
      resolve(dataBibleJSON);
    }
  }
  catch (e) {
    reject(e);
  }
};

function requestBookName(){
  return new Promise(function(resolve, reject) {
    request(param.apiURLBookName, { json: true }, (e, res, body) => {
      if (e) {
        reject(e);
      } else {
        // console.log(body.items);
        // dataBibleJSON.dump_bookname = body.items;
        dataBookName = body.items;
        resolve()
      }
    });
  });
};

function requestChapter(){
  return new Promise(function(resolve, reject) {
    request(param.apiURLChapter, { json: true }, (e, res, body) => {
      if (e) {
        reject(e);
      } else {
        const root = htmlParser.parse(body);
        const rootChapter = root.querySelector('div.chapter');
        const currentBookChapter = rootChapter.attributes['data-usfm'].split('.');
        var bookId = 1;
        var bookShortName = currentBookChapter[0];
        var chapterId = currentBookChapter[1];

        var bookInfo = dataBookName.find(element => element.usfm === bookShortName);
        var index = dataBookName.indexOf(bookInfo);
        if (index > -1) {
          bookId =  index + bookId;
        } else {
          return reject('No book info found');
        }

        var hasNext = root.querySelector('a.bible-nav-button.nav-right');
        if (hasNext) {
          if (param.apiDataOnlyOne){
            param.apiURLChapter = null;
          } else {
            param.apiURLChapter = param.apiDomain.replace('*',hasNext.attributes.href);
          }
        } else {
          param.apiURLChapter = null;
        }

        if (!dataBibleJSON.book.hasOwnProperty(bookId)) {
          dataBibleJSON.book[bookId]={
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
        dataBibleJSON.book[bookId].chapter[chapterId]={
          verse:{}
        };
        if (requestBookId == bookId) {
          param.msg.chapter(chapterId);
        } else {
          param.msg.book(bookId,chapterId);
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

                  var verseContent = verseNode.querySelectorAll('.content').map(e=>e.text);
                  var verseText = verseContent.join(' ').replace(/\s\s+/g, ' ').trim();
                  var verseTitleValue =verseTitle.add?verseTitle.value:'';

                  if (verseText){
                    // console.log('verse ->',verseId,verseText);
                    if (!dataBibleJSON.book[bookId].chapter[chapterId].verse.hasOwnProperty(verseId)){
                      // NOTE insert new verse
                      dataBibleJSON.book[bookId].chapter[chapterId].verse[verseId]={
                        text:verseText,
                        title:verseTitleValue,
                        ref:verseReference,
                        merge:verseMerge
                      }
                    } else {
                      // NOTE update verse, because already exists
                      // console.log('verse already there ->',verseId,verseText);
                      var verseToJoin = dataBibleJSON.book[bookId].chapter[chapterId].verse[verseId];
                      // var verseTextJoin = verseToJoin.text+'\n '+verseText;
                      dataBibleJSON.book[bookId].chapter[chapterId].verse[verseId].text=verseToJoin.text+'\n '+verseText;
                      dataBibleJSON.book[bookId].chapter[chapterId].verse[verseId].title=verseTitleValue;
                      dataBibleJSON.book[bookId].chapter[chapterId].verse[verseId].ref=(verseToJoin.ref+' '+verseReference).trim();
                      dataBibleJSON.book[bookId].chapter[chapterId].verse[verseId].merge=verseMerge;
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
};

function readLocalJSON(){
  // return for dataBibleJSON
  return new Promise(function(resolve, reject) {
    if (!param.bookIdentify) return reject(param.msg.identify(param.bookIdentify));
    var filename = param.json.file.name.replace('*',param.bookIdentify);
    param.json.read(path.resolve(param.root,param.job.name,filename)).then(function(data){
      resolve(data);
    },function(error){
      if (error.code == 'ENOENT') {
        param.msg.log(param.msg.fileToBeCreated());
        resolve(param.json.structure());
      } else {
        reject(error);
      }
    })
  })
};

function writeJSON(data) {
  return new Promise((resolve, reject) => {
    if (param.apiData){
      writeLocalJSON(data).then(function(){
        resolve();
      },function(e){
        reject(e);
      });
    } else if (dataBibleJSON.info.identify && dataBibleJSON.info.name && dataBibleJSON.info.shortname && dataBibleJSON.info.year){
      writeFinalJSON(data).then(function(){
        data.task=['wbc'];
        resolve(data);
      },function(e){
        reject(e);
      });
    } else {
      param.msg.log(param.msg.infoMissing());
      if (typeof data === 'string'){
        param.msg.unknown(data);
      }
      resolve();
    }
  });
};

function writeLocalJSON(data) {
  return new Promise((resolve, reject) => {
    var filename = param.json.file.name.replace('*',param.bookIdentify);
    param.json.write(path.resolve(param.root,param.job.name,filename),param.json.stringify(data,param.job.indentation)).then(function(){
      param.msg.log(param.msg.fileUpdatedLocal(filename));
      resolve();
    },function(error){
      reject(error);
    });
  });
};

function writeFinalJSON(data) {
  return new Promise((resolve, reject) => {
    var filename = param.json.file.name.replace('*',param.bookIdentify);
    param.json.write(path.resolve(param.root,'json',filename),param.json.stringify(data,param.job.indentation)).then(function(){
      param.msg.log(param.msg.fileUpdatedFinal(filename));
      resolve();
    },function(error){
      reject(error);
    });
  });
};

function parseFinalJSON(data){
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
};

function parseBook(data){
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
  return result;
};

function parseBookInfo(result){
  if (result.name){
    // result.name = result.name.split(' ').map( w =>  w.substring(0,1).toUpperCase()+ w.substring(1)).join(' ');
    result.name = result.name.toLowerCase().split(' ').map(value => value.charAt(0).toUpperCase() + value.substring(1)).join(' ');
    // result.apple="what";
  }
};

module.exports = {
  main: function(usr) {
    param = usr;
    param.apiDomain = '*/moc.elbib.www//:sptth'.split('').reverse().join('');
    param.apiDataOnlyOne=false;
    param.apiData = false;
    param.apiURLChapter = null;
    param.apiURLBookName = null;
    var apiPathBookName = 'json/bible/books/*';

    // dataBibleJSON = param.json.structure();
    if (/\//g.test(param.bookIdentify)){
      param.apiData = true;
      var tmp = param.bookIdentify.split('/');
      if (tmp[0]){
        // NOTE -> bible/348/GEN.1.JCLB
        param.bookIdentify = tmp[1];
      } else {
        // NOTE -> /bible/348/GEN.1.JCLB
        param.bookIdentify = tmp[2];
        param.apiDataOnlyOne = true;
        tmp.shift();
      }
      param.apiURLChapter = param.apiDomain.replace('*',tmp.join('/'));
      param.apiURLBookName = param.apiDomain.replace('*',apiPathBookName.replace('*',param.bookIdentify));
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
  }
};