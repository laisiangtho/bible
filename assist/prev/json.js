const path = require('path');
// const fs = require('fs-extra');
// const sqlite3 = require('sqlite3');
var param={};

var json = {
  // category:{}
  fileTask:function(){
    // return path.resolve(param.root,'json',param.task.json.extension.replace('*',param.bookIdentify));
    return path.resolve(param.root,'json',param.json.file.name.replace('*',param.bookIdentify));
  },
  fileCategory:function(){
    return path.resolve(param.root,param.json.file.name.replace('*','category'));
  }
};

function readJSON() {
  return new Promise(function(resolve, reject) {
    if (!param.bookIdentify) return reject(`...\x1b[35m${param.bookIdentify}\x1b[0m!`);
    param.json.read(json.fileCategory()).then(function(category){
      json.category = category;
      param.json.read(json.fileTask()).then(function(e){
        resolve(e);
      },function(e){
        reject(e);
      });
    },function(e){
      reject(e);
    });
  });
};

function writeJSON(data) {
  var indentation = param.args.length > 2;
  return param.json.write(json.fileTask(),param.json.stringify(data,indentation));
};

function scanJSON(data){
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
     resolve(result);
    } catch (e) {
      reject(e);
    }
  });
};

function parseInfo(data){
  return data;
};

function parseNote(data){
  return data;
};

function parseDigit(data){
  return data;
};

function parseLanguage(data){
  return data;
};

function parseTestament(data){
  return data;
};

function parseStory(data){
  return data;
};

function parseBook(data){
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
        param.msg.book(logBookId,null,book.info.name);
        // param.msg.book(logBookId,null);
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
              param.msg.chapter(verseStatus);
            } else {
              param.msg.chapter(`\x1b[31m${cId}\x1b[0m?`);
            }
          }
        }
      } else {
        // console.log('has no chapter');
        param.msg.chapter('no chapter');
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

module.exports = {
  main: async function(usr) {
    param = usr;

    try {
      const result = await readJSON();
      try {
        await scanJSON(result);
        return Promise.resolve();
      }
      catch (e) {
        return Promise.reject(e);
      }
    }
    catch (error) {
      return Promise.reject(error);
    }
  }
};