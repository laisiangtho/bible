const path = require('path'), fs = require('fs-extra'), sqlite3 = require('sqlite3');
var task = module.exports = {}, settings={};

var json = {
  // category:{}
  fileTask:function(){
    return path.resolve(settings.rootDirectory,settings.task.json.dirname,settings.task.json.extension.replace('*',settings.bookIdentify));
  },
  fileCategory:function(){
    return path.resolve(settings.rootDirectory,settings.task.json.extension.replace('*','category'));
  }
},

readJSON = function() {
  return new Promise(function(resolve, reject) {
    if (!settings.bookIdentify) return reject(`...\x1b[35m${settings.bookIdentify}\x1b[0m!`);
    settings.json.read(json.fileCategory()).then(function(category){
      json.category = category;
      settings.json.read(json.fileTask()).then(function(e){
        resolve(e);
      },function(e){
        reject(e);
      });
    },function(e){
      reject(e);
    });
  });
},
writeJSON = function(data) {
  var indentation = settings.args.length > 2;
  var tmp = settings.json.stritify(data,indentation);
  return settings.json.write(json.fileTask(),tmp);
},
scanJSON = function(data){
  return new Promise(function(resolve, reject) {
    try {
      var result={
        info:parseInfo(data.info),
        note:parseNote(data.note),
        digit:parseDigit(data.digit),
        language:parseLanguage(data.language),
        testament:parseTestament(data.testament),
        story:parseStory(data.story),
        book:parseBook(data.book)
      };
     return resolve();
    } catch (e) {
      return reject(e);
    }
  });
},
parseInfo = function(data){
  return data;
},
parseNote = function(data){
  return data;
},
parseDigit = function(data){
  return data;
},
parseLanguage = function(data){
  return data;
},
parseTestament = function(data){
  return data;
},
parseStory= function(data){
  return data;
},
parseBook = function(data){
  var categoryBook = json.category.book;
  var bookTofix = 0;
  var bookTotal = Object.keys(categoryBook).length;
  var bookCount = 0;
  var chapterTofix = 0;
  var verseTofix = 0;
  var result={};
  for (const bId in data) {
    if (data.hasOwnProperty(bId)) {
      bookCount++;
      var categoryBookCurrent = categoryBook[bId];
      const book = data[bId];
      if (book.hasOwnProperty('chapter')){
        var chapterTotal = categoryBookCurrent.c;
        var chapterCount = Object.keys(book.chapter).length;
        var logBookId = bId;
        if (chapterCount != chapterTotal){
          logBookId = logBookId+`\x1b[0m(\x1b[31m${chapterTotal}-${chapterCount}\x1b[0m)`;
          chapterTofix++;
        }
        settings.message.book(logBookId,null,book.info.name);
        // settings.message.book(logBookId,null);
        // console.log(book.info);

        // var bookLength = book.info.name.length;
        // var bookNameWithSpace = book.info.name + new Array(30 - bookLength).join(' ');
        result[bId]={
          chapter:{}
        };
        for (const cId in book.chapter) {
          if (book.chapter.hasOwnProperty(cId)) {
            const chapter = book.chapter[cId];
            if (chapter.hasOwnProperty('verse')){
              result[bId].chapter[cId]={
                verse:{}
              };
              var verseTotal = categoryBookCurrent.v[cId-1];
              var verseCount = Object.keys(chapter.verse).length;
              if (verseCount != verseTotal){
                verseTofix++;
              }
              for (const vId in chapter.verse) {
                if (chapter.verse.hasOwnProperty(vId)) {
                  var newVerse={};
                  const verse = chapter.verse[vId];
                  if (verse.hasOwnProperty('text') && verse.text !="") {
                    newVerse.text=verse.text;
                  } else {
                    console.log('verse has no text',bId,cId,vId);
                  }
                  if (verse.hasOwnProperty('title') && verse.title !="") newVerse.title=verse.title;
                  if (verse.hasOwnProperty('merge') && verse.merge !="") {
                    verseTofix--;
                    newVerse.merge=verse.merge;
                  }
                  if (verse.hasOwnProperty('ref') && verse.ref !="") newVerse.ref=verse.ref;
                  result[bId].chapter[cId].verse[vId]=newVerse;
                }
              }
              var verseStatus = verseCount == verseTotal?cId:`${cId}(\x1b[31m${verseTotal}-${verseCount}\x1b[33m)`;
              settings.message.chapter(verseStatus);
            } else {
              settings.message.chapter(`\x1b[31m${cId}\x1b[0m?`);
            }
          }
        }
      } else {
        // console.log('has no chapter');
        settings.message.chapter('no chapter');
        bookTofix++;
      }
    }
  }
  var bookPassed = bookTofix == 0;
  var chapterPassed = chapterTofix == 0;
  var versePassed = verseTofix == 0;
  // var tofixed = bookTofix + chapterTofix + verseTofix;
  console.log(`\n...status > book: \x1b[31m${bookPassed}\x1b[0m chapter: \x1b[31m${chapterPassed}\x1b[0m verse: \x1b[31m${versePassed}\x1b[0m`);
  console.log(`...to fix > book: \x1b[31m${bookTofix}\x1b[0m chapter: \x1b[31m${chapterTofix}\x1b[0m verse: \x1b[31m${verseTofix}\x1b[0m`);
  // data.forEach(function(bid){
  //   console.log('bookid',bid);
  // });
  return result;
};

task.main = function(parentSettings) {
  settings = parentSettings;
  return new Promise(function(resolve, reject) {
    readJSON().then(function(resultOrginal){
      // console.log(resultOrginal);
      scanJSON(resultOrginal).then(function(resultFinal){
        resolve();
        // return writeJSON(resultFinal).then(function(e){
        //   // resolve(resultFinal);
        //   resolve();
        // },function(e){
        //   reject(e);
        // })
      },function(e){
        reject(e);
      });
    },function(e){
      reject(e);
    });
    // readJSON().then(function(result){
    //   databasePrepare(result).then(function(){
    //     result.task=['json','sqlite'];
    //     // var taskIdentify = settings.taskIdentify, taskTarget = settings.task[taskIdentify].target;
    //     // result.task=[taskIdentify,taskTarget];
    //     resolve(result);
    //   },function(e){
    //     reject(e);
    //   });
    // },function(error){
    //   reject(error);
    // });
  });
};
