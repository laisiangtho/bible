const path = require('path'), fs = require('fs-extra'), sqlite3 = require('sqlite3');
var task = module.exports = {}, settings={};

var readJSON = function(data) {
  return new Promise((resolve, reject) => {
    var tmp = settings.bookSourceJSON.replace('*',settings.bookIdentify);
    if (!settings.bookIdentify) return reject(`...\x1b[35m${settings.bookIdentify}\x1b[0m!`);
    fs.exists(tmp, function(e) {
      if (e) {
        try {
          var o=fs.readFileSync(tmp).toString();
          resolve(JSON.parse(o));
        } catch (e) {
          reject(e)
        }
      } else {
        reject(`...\x1b[35mdoes not\x1b[0m exist!`);
      }
    });
  });
},
databaseConnection = null,
databasePrepare = function(data){
  return new Promise((resolve, reject) => {
    var db = settings.bookTargetSQLite.replace('*',settings.bookIdentify);

    fs.unlink(db,function(){
      // databaseConnection = new sqlite3.Database(':memory:');
      // ,sqlite3.OPEN_READWRITE
      databaseConnection = new sqlite3.Database(db);
      // databaseConnection.configure('busyTimeout',1000);
      databaseConnection.serialize(function() {
        // NOTE: testament
        databaseConnection.run("CREATE TABLE IF NOT EXISTS testament (tid INTEGER, name TEXT, shortname TEXT)");
        // NOTE: book
        databaseConnection.run("CREATE TABLE IF NOT EXISTS book (bid INTEGER, name TEXT, shortname TEXT, desc TEXT, abbr TEXT)");
        // NOTE: book
        databaseConnection.run("CREATE TABLE IF NOT EXISTS story (bid INTEGER, cid INTEGER, vid INTEGER, text TEXT, ref TEXT)");
        // NOTE: bible -> , merged INTEGER, title TEXT, ref TEXT
        databaseConnection.run("CREATE TABLE IF NOT EXISTS bible (bid INTEGER, cid INTEGER, vid INTEGER, verse TEXT)");
        // NOTE: prepare insert
        databaseInsert(data).then(()=>{
          resolve()
        },(e)=>{
          reject(e);
        }).then(()=>{
          databaseConnection.close();
        })
      });
    });
  });
},
databaseInsert = function(value){
  return new Promise((resolve, reject) => {
    let taskPrimary = [];
    taskPrimary.push(databaseTestament(value.testament));
    taskPrimary.push(databaseBook(value.book));

    // let bible = value.bible;
    // for (const bId in bible) {
    //   if (bible.hasOwnProperty(bId)) {
    //     var book = bible[bId];
    //     for (const cId in book) {
    //       if (book.hasOwnProperty(cId)) {
    //         const chapter = book[cId];
    //         taskPrimary.push(databaseBible(Number(bId), Number(cId), chapter));
    //       }
    //     }
    //   }
    // }
    let story = value.story;
    for (const bId in story) {
      if (story.hasOwnProperty(bId)) {
        var book = story[bId];
        for (const cId in book) {
          if (book.hasOwnProperty(cId)) {
            const chapter = book[cId];
            taskPrimary.push(databaseStory(Number(bId), Number(cId), chapter));
          }
        }
      }
    }
    let bible = value.book;
    for (const bId in bible) {
      if (bible.hasOwnProperty(bId)) {
        var book = bible[bId].chapter;
        for (const cId in book) {
          if (book.hasOwnProperty(cId)) {
            const chapter = book[cId].verse;
            taskPrimary.push(databaseBible(Number(bId), Number(cId), chapter));
          }
        }
      }
    }
    Promise.all(taskPrimary).then(()=>{
      resolve();
    }).catch(error=>{
      reject(error);
    })
  });
},
databaseTestament = function(testament){
  return new Promise((resolve, reject) => {
    var table = databaseConnection.prepare("INSERT INTO testament (tid, name, shortname) VALUES (?,?,?)");
    for (const tId in testament) {
      if (testament.hasOwnProperty(tId)) {
        const o = testament[tId].info;
        table.run([tId, o.name, o.shortname]);
      }
    }
    table.finalize(()=>{
      resolve()
    });
  })
},
databaseBook = function(value){
  return new Promise((resolve, reject) => {
    var table = databaseConnection.prepare("INSERT INTO book (bid, name, shortname, desc, abbr) VALUES (?,?,?,?,?)");
    for (const bId in value) {
      if (value.hasOwnProperty(bId)) {
        const book = value[bId].info;
        table.run([bId, book.name, book.shortname, book.desc, book.abbr.join(',')]);
      }
    }
    table.finalize(()=>{
      resolve()
    });
  })
},
databaseBibleCurrentBook=0,
databaseBible = function(bId, cId, chapter){
  return new Promise((resolve, reject) => {
    // , merged, title, ref -> ,?,?,?
    var table = databaseConnection.prepare("INSERT INTO bible (bid, cid, vid, verse) VALUES (?,?,?,?)");
    for (const vId in chapter) {
      if (chapter.hasOwnProperty(vId)) {
        const verse = chapter[vId];
        // table.run([bId,cId, Number(vId),verse.text, verse.merge,verse.title,verse.ref]);
        table.run([bId,cId, vId,verse.text]);
      }
    }
    table.finalize(()=>{
      if (databaseBibleCurrentBook < bId) {
        databaseBibleCurrentBook = bId;
        settings.message.book(bId,cId);
      } else {
        settings.message.chapter(cId);
      }
      resolve()
    })
  });
};
databaseStoryCurrentBook=0,
databaseStory = function(bId, cId, chapter){
  return new Promise((resolve, reject) => {
    // story (bid INTEGER, cid INTEGER, vid INTEGER, text TEXT, ref TEXT)
    var table = databaseConnection.prepare("INSERT INTO story (bid, cid, vid, text,ref) VALUES (?,?,?,?,?)");
    for (const vId in chapter) {
      if (chapter.hasOwnProperty(vId)) {
        const story = chapter[vId];
        table.run([bId,cId, vId,story.text,story.ref]);
      }
    }
    table.finalize(()=>{
      if (databaseStoryCurrentBook < bId) {
        databaseStoryCurrentBook = bId;
        settings.message.book(bId,cId);
      } else {
        settings.message.chapter(cId);
      }
      resolve()
    })
  });
};

task.main = function(parentSettings) {
  settings = parentSettings;
  databaseBibleCurrentBook = 0;
  databaseStoryCurrentBook = 0;
  return new Promise(function(resolve, reject) {
    readJSON().then(function(result){
      databasePrepare(result).then(function(){
        result.task=['json','sqlite'];
        resolve(result);
      },function(e){
        reject(e);
      });
    },function(error){
      reject(error);
    });
  });
};
