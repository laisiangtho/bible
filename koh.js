const path = require('path'), fs = require('fs-extra');
var task = module.exports = {}, settings={};

var readJSON = function(){
  return new Promise(function(resolve, reject) {
    if (!settings.bookIdentify) return reject(`...\x1b[35m${settings.bookIdentify}\x1b[0m!`);
    var sourceFile = path.resolve(settings.rootDirectory,settings.task.koh.dirname,settings.task.koh.extension.replace('*',settings.bookIdentify));
    fs.readFile(sourceFile, function(e, data) {
      if (e) {
        if (e.code == 'ENOENT') {
          return reject(`...\x1b[35mdoes not\x1b[0m exist!`);
        }
        reject(e);
      } else {
        try {
          resolve(parseStructure(JSON.parse(data)));
        } catch (e) {
          return reject(e);
        }
      }
    });
  })
},
prepareJSON = function(data) {
  return new Promise((resolve, reject) => {
    var bookSourceJSONName = settings.task.json.extension.replace('*',settings.bookIdentify);
    var bookSourceJSON = path.resolve(settings.rootDirectory,settings.task.json.dirname,bookSourceJSONName);
    fs.writeFile(bookSourceJSON, stringifyJSON(data),function(error){
      if (error) {
        reject(error);
      } else {
        console.log(`\n...updated\x1b[32m ${bookSourceJSONName}\x1b[0m!`);
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
parseStructure = function(data) {
  var result={
    info:parseInfo(data.info),
    note:{},
    digit:parseDigitName(),
    language:parseLanguage(data.language),
    testament:parseTestamentName(data.testament),
    story:parseStory(),
    book:parseBookEach(data)
  };
  return result;
},
parseInfo = function(data){
  return data;
},
parseDigitName = function(data){
  return ["0","1","2","3","4","5","6","7","8","9"];
},
parseLanguage = function(data){
  return data;
},
parseTestamentName = function(data){
  return data;
},
parseStory = function(){
  return {};
},
parseBookEach = function(data){
  var result={};
  var bookId = 0;
  var tmpbookName = [];
  for (var book of data.dump) {
    var bookTitle = book.title.replace(/\s\s+/g, ' ').trim();
        bookTitle = bookTitle.split(' ').map(w => w[0].toUpperCase() + w.substr(1).toLowerCase()).join(' ');
    var lastIndex = bookTitle.lastIndexOf(" ");
    var bookName = bookTitle.substring(0, lastIndex);
    var chapterId = bookTitle.split(" ").pop();
    if (!tmpbookName.includes(bookName)) {
      tmpbookName.push(bookName);
      bookId++;
    }
    if (!result.hasOwnProperty(bookId)){
      result[bookId]={
        info:{
          name:bookName,
          shortname:bookName.replace(/\s/g, '').substring(0, 4),
          abbr:[],
          desc: ''
        },
        topic:{},
        chapter:{}
      };
    }

    var dumpVerses = book.content.replace(/\s\s+/g, ' ').trim();
    dumpVerse = dumpVerses.split('\n').map((e)=>e.trim());

    var verses ={};
    var titles =[];
    for (let index = 0; index < dumpVerse.length; index++) {
      const verse = dumpVerse[index].replace(/\s+/g, ' ').trim();
      // NOTE kachin version has some dot ended
      var verseId = verse.split(" ")[0].trim().replace('.','');
      // var verseTitel = titles.length?titles[0]:'';

      if (isNaN(verseId) === false) {
        verses[verseId]={
          text:verse.substr(verse.indexOf(" ") + 1)
          // title:'', ref:'', merge:''
        };
        if (titles.length){
          verses[verseId].title=titles.pop();
        }
      } else if (verseId.includes("-")) {
        // NOTE verse merge
        var verseMergeId = verseId.split("-");
        if (isNaN(verseMergeId[0]) === false && isNaN(verseMergeId[1]) === false) {
          verses[verseMergeId[0]]={
            text:verse.substr(verse.indexOf(" ") + 1),
            merge:verseMergeId[1]
          };
          console.log('merge?? -> ',bookName,chapterId,verseId);
        } else {
          titles.push(verse)
        }

      } else {
        titles.push(verse)
      }
    }
    if (titles.length > 1) {
      console.log('problem?? -> verse has no Id',bookName,chapterId,titles);
      // result[bookId].chapter[chapterId]={
      //   title:titles
      // };
    }
    result[bookId].chapter[chapterId]={
      verse:verses
    };
  }
  return result;
};

task.main = function(parentSettings) {
  settings = parentSettings;
  databaseBibleCurrentBook = 0;
  return new Promise(function(resolve, reject) {
    readJSON().then(function(result){
      prepareJSON(result).then(function(){
        result.task=['koh','json'];
        // var taskIdentify = settings.taskIdentify, taskTarget = settings.task[taskIdentify].target;
        // result.task=[taskIdentify,taskTarget];
        // resolve(result);
        resolve(result);
      },function(e){
        reject(e);
      });
    },function(error){
      reject(error);
    });
  });
};
