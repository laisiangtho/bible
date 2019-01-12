const path = require('path'), fs = require('fs-extra'), sqlite3 = require('sqlite3');
var task = module.exports = {}, settings={};

var result={
  info:{
    identify: settings.bookIdentify,
    name: '',
    shortname: '',
    year: '',
    language: {
      text: "",
      textdirection: "ltr",
      name: "en"
    },
    version: 1,

  },
  note:{},
  digit:[],
  language:{},
  testament:{
    1: {
      info: {
        name: "Old Testament",
        shortname: "OT"
      },
      other: {}
    },
    2: {
      info: {
        name: "New Testament",
        shortname: "NT"
      },
      other: {}
    }
  },
  story:{},
  book:{}
},
readSQLite=function(){
  return new Promise((resolve, reject) => {
    var db = settings.bookSourceSQLite.replace('*',settings.bookIdentify);
    if (!settings.bookIdentify) return reject(`...\x1b[35m${settings.bookIdentify}\x1b[0m!`);
    fs.exists(db, function(e) {
      if (e){
        dbConnection = new sqlite3.Database(db,sqlite3.OPEN_READONLY);
        dbConnection.serialize(function() {
          dbSelect().then(()=>{
            resolve(result)
          },(e)=>{
            reject(e);
          }).then(()=>{
            dbConnection.close();
          });
        });
      } else {
        reject(`...\x1b[35mdoes not\x1b[0m exist!`);
      }
    })
  });
},
dbSelect = function(){
  var tasks=[];
  tasks.push(dbSelectInfo());
  tasks.push(new Promise(function(resolve, reject) {
    dbSelectBookName().then(function(raw){
      dbSelectBible(raw).then(function(){
        resolve();
      },function(e){
        reject(e)
      })
    },function(e){
      reject(e)
    })
  }));
  return Promise.all(tasks);
},
dbSelectInfo = function() {
  return new Promise((resolve, reject) => {
    result.info.identify=settings.bookIdentify;
    result.info.shortname=settings.bookIdentify;
    dbConnection.all("SELECT * FROM info",function(e,raw){
      if (e) return reject(e);
      for (const o of raw) {
        if (o.name == 'description') result.info.description=o.value;
        if (o.name == 'language') {
          result.info.language.name=o.value;
          if (settings.bookCollection.language.hasOwnProperty(o.value)){
            var language = settings.bookCollection.language[o.value];
            // result.info.language.text=lang.text;
            // result.info.language.textdirection=lang.textdirection;
            for (const langId in language) {
              if (language.hasOwnProperty(langId)) {
                var element = language[langId];
                result.info.language[langId]=language[langId];
              }
            }
          }
        }
        if (o.name == 'detailed_info') result.info.publisher=o.value;
        if (o.name == 'chapter_string') result.language.chapter=o.value;
        if (o.name == 'chapter_string_ps') result.language.verse=o.value;
        if (o.name == 'introduction_string') result.language.introduction=o.value;
        if (o.name == 'digits0-9') result.digit=o.value.split('');
      }
      resolve();
    });
  })
},
// dbSelectBookList=[],
dbSelectBookName = function() {
  return new Promise((resolve, reject) => {
    // WHERE is_present=1 ORDER BY sorting_order ASC
    dbConnection.all("SELECT * FROM books_all",function(e,raw){
      if (e) {
        dbConnection.all("SELECT * FROM books",function(e,raw){
          if (e) return reject(e);
          dbSelectBookNameProcess(raw).then(function(r){
            resolve(r);
          },function(e){
            reject(e);
          })
        })
      } else {
        dbSelectBookNameProcess(raw).then(function(r){
          resolve(r);
        },function(e){
          reject(e);
        })
      }
      // if (e) return reject(e);
      // raw.sort(function (a, b) {
      //   return a.sorting_order - b.sorting_order;
      // }).map(function(item,index){
      //   var bId = index+1;
      //   result.book[bId]={
      //     info:{
      //       name: item.long_name,
      //       shortname: item.short_name.replace(/\s+/g,'').replace(/\./g,''),
      //       abbr:[],
      //       desc: item.title
      //     },
      //     topic:[],
      //     chapter:{}
      //   }
      //   delete item.book_color;
      //   delete item.sorting_order;
      //   delete item.is_present;
      //   delete item.long_name;
      //   delete item.short_name;
      //   delete item.title;
      //   return item.bId = bId;
      // });
      // resolve(raw);
    });
  })
},
dbSelectBookNameProcess = function(raw) {
  return new Promise((resolve, reject) => {
    raw.sort(function (a, b) {
      return a.sorting_order - b.sorting_order;
    }).map(function(item,index){
      var bId = index+1;
      result.book[bId]={
        info:{
          name: item.long_name,
          shortname: item.short_name.replace(/\s+/g,'').replace(/\./g,''),
          abbr:[],
          desc: item.title
        },
        topic:[],
        chapter:{}
      }
      delete item.book_color;
      delete item.sorting_order;
      delete item.is_present;
      delete item.long_name;
      delete item.short_name;
      delete item.title;
      return item.bId = bId;
    });
    resolve(raw);
  })
},
dbSelectBible = function(taskList) {
  var processChapter=function(book){
    return new Promise((resolve, reject) => {
      dbConnection.all("SELECT book_number, chapter FROM verses WHERE book_number=? GROUP BY chapter",[book.book_number],function(e,raw){
        if (e) return reject(e);
        var tasksChild=[];
        // settings.message.book(book.bId,raw.map(e=>e.chapter));
        for (const o of raw) {
          result.book[book.bId].chapter[o.chapter]={};
          tasksChild.push(new Promise((resolve, reject) => {
            processVerse(o).then(function(responseVerses){
              result.book[book.bId].chapter[o.chapter].verse = responseVerses;
              resolve();
            },function(e){
              reject(e)
            })
          }));
        }
        Promise.all(tasksChild).then(function(){
          resolve();
        },function(e){
          resolve(e);
        });
      });
    });
  };
  var processVerse=function(book){
    return new Promise((resolve, reject) => {
      dbConnection.all("SELECT verse, text FROM verses WHERE book_number=? AND chapter=?",[book.book_number,book.chapter],function(e,raw){
        if (e) return reject(e);
        var tmp={};
        for (const o of raw) {
          tmp[o.verse]={};
          tmp[o.verse].text=o.text;
        }
        resolve(tmp);
      });
    });
  };
  var processStoryReject='';
  var processStory=function(book){
    return new Promise((resolve, reject) => {
      dbConnection.all("SELECT chapter, verse, title FROM stories WHERE book_number=?",[book.book_number],function(e,raw){
        if (e) {
          if (!processStoryReject) {
            processStoryReject=true;
            // console.log(e.message,e.code);
            var message = e.message.toString().replace(e.code,'').replace(/:\s+/,'');
            console.log(`...skip\x1b[35m ${message}\x1b[0m`);
            // console.log(`...skip writing\x1b[35m ${e.message}\x1b[0m`);
            
          }
          return resolve();
        }
        // var tasksChild=[];
        for (const o of raw) {
          if (!result.story.hasOwnProperty(book.bId)) result.story[book.bId]={};
          if (!result.story[book.bId].hasOwnProperty(o.chapter)) result.story[book.bId][o.chapter]={};
          result.story[book.bId][o.chapter][o.verse] = {
            text:o.title
          };
        }
        resolve();
      });
    });
  };
  var tasks=[];
  for (const book of taskList) {
    tasks.push(new Promise(function(resolve, reject) {
      processChapter(book).then(function(){
        resolve();
      },function(e){
        reject(e)
      })
    }));
    tasks.push(new Promise(function(resolve, reject) {
      processStory(book).then(function(){
        resolve();
      },function(e){
        reject(e)
      })
    }));
  }
  return Promise.all(tasks);
},
jsonPrepare = function(data) {
  return new Promise((resolve, reject) => {
    fs.writeFile(settings.bookSourceJSON.replace('*',settings.bookIdentify), jsonStringify(data),function(error){
      if (error) {
        reject(error);
      } else {
        console.log(`...updated\x1b[32m ${settings.bookIdentify}\x1b[0m!`);
        resolve();
      }
    });
  });
},
jsonStringify = function(data) {
  if (settings.args.length > 2) {
    return JSON.stringify(data, null, 2);
  } else {
    return JSON.stringify(data);
  }
};

task.main = function(parentSettings) {
  settings = parentSettings;
  databaseBibleCurrentBook = 0;
  return new Promise(function(resolve, reject) {
    readSQLite().then(function(result){
      jsonPrepare(result).then(async function(){
        // for (const bId in result.book) {
        //   if (result.book.hasOwnProperty(bId)) {
        //     await settings.message.book(bId,Object.keys(result.book[bId].chapter));
        //   }
        // }
        // sv-sv17.1917,sv-sfb98.1998,sv-sfb15.2015
        result.task=['ph4','json'];
        resolve(result);
      },function(e){
        reject(e);
      });
      // console.log(result.book);
      // resolve();
    },function(error){
      reject(error);
    });
  });
};
