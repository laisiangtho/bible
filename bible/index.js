const path = require('path'), fs = require('fs-extra'), xml2js = require('xml2js'), sqlite3 = require('sqlite3');
// const fs = require('fs-extra'), xml2js = require('xml2js');
var args = process.argv.slice(2);
// args.unshift('tmp');
/**
 * NOTE: node lang {filename:1/2/3} {option:sqlite,json} {true}
 * if option is json then there is thrid argument JSON.stringify would format
 *
 *  */


var xmlParser = new xml2js.Parser({
  mergeAttrs: true,
  charkey:'text',
  explicitArray:false,
  explicitRoot:false,
  explicitCharkey:true
  // tagNameProcessors: [tagNameProcessors],
  // attrNameProcessors: [attrNameProcessors],
  // valueProcessors: [valueProcessors],
  // attrValueProcessors: [attrValueProcessors ]
}),
bookId = args[0],
currentDirectory = path.dirname(require.main.filename),
// currentPath = process.cwd(),
bookCollectionJSON = path.resolve(currentDirectory,'book.json'),
bookSource= path.resolve(currentDirectory,'xml','*.xml'),
bookTargetJSON = path.resolve(currentDirectory,'json','*.json'),
bookTargetSQLite = path.resolve(currentDirectory,'sqlite','*.db'),
xmlRead = function(){
  return new Promise(function(resolve, reject) {
    fs.readFile(bookSource.replace('*',bookId), function(e, data) {
      if (e) return reject(e);
      xmlParser.parseString(data, function (e, result) {
        if (e) return reject(e);
        var result_custom = parseStructure(result);
        resolve(result_custom);
      });
    });
  })
},
jsonPrepare = function(data) {
  return new Promise((resolve, reject) => {
    fs.writeFile(bookTargetJSON.replace('*',bookId), jsonStringify(data),function(error){
      if (error) {
        reject(error);
      } else {
        resolve();
      }
    });
  });
},
jsonStringify = function(data) {
  if (args.length > 2) {
    return JSON.stringify(data, null, 2);
  } else {
    return JSON.stringify(data);
  }
},
parseStructure = function(data) {
  var result={
    info:parseInfo(data.info),
    note:{},
    digit:parseDigitName(data.digit),
    language:parseLanguage(data.language),
    testament:parseTestamentName(data.testament),
    story:parseStory(data.book),
    book:parseBookEach(data.book)
  };
  return result;
},
parseInfo = function(data){
  var result={};
  for (var row of data) {
    if (row.hasOwnProperty('id') && row.hasOwnProperty('text')){
      if (Object.keys(row).length > 2){
        result[row.id]=row;
        delete row.id;
      } else {
        result[row.id]=row.text;
      }
    }
  }
  return result;
},
parseDigitName = function(data){
  if (data) {
    var result=[];
    for (var digit of data) {
      result.push(digit.text)
    }
    return result;
  }
  return ["0","1","2","3","4","5","6","7","8","9"];
},
parseLanguage = function(data){
  var result={};
  if (data) {
    for (var row of data) {
      if (row.hasOwnProperty('id') && row.hasOwnProperty('text')){
        result[row.id]=row.text;
      }
    }
  }
  return result;
},
parseTestamentName = function(data){
  var result={};
  for (var testament of data) {
    result[testament.id]={};
    if (testament.hasOwnProperty('text')){
      testament.desc = testament.text;
      delete testament.text;
    }
    result[testament.id].info=testament;
    result[testament.id].other={};
    delete testament.id;
  }
  return result;
},
parseStory = function(data){
  var result={};
  for (var book of data) {
    if (book.content){
      // console.log(book.id);
      for (var row of book.content) {
        if (row.hasOwnProperty('ref') && row.hasOwnProperty('text')){
          if (!result.hasOwnProperty(book.id)){
            result[book.id]={}
          }
          var tmp = row.ref.split(',')[0].split('.');
          var chapter = tmp[1], verse = tmp[2];

          if (!result[book.id].hasOwnProperty(chapter)){
            result[book.id][chapter]={};
          }
          // if (!result[book.id][chapter].hasOwnProperty(verse)){
          //   result[book.id][chapter][verse]={};
          // }
          // result[book.id]=row;
          result[book.id][chapter][verse]=row;
        }
      }
    }
  }
  return result;
},
parseBookEach = function(data){
  var result={};
  for (var book of data) {
    result[book.id]={
      info:{
        name:book.name,
        shortname:book.shortname,
        abbr:[],
        desc: ''
      },
      topic:{}
    };
    if (book.hasOwnProperty('info') && book.info.hasOwnProperty('text')) {
      result[book.id].info.desc=book.info.text;
    }
    result[book.id].chapter=parseBookChapter(book,book.id);
  }
  return result;
},
parseBookChapter = function(book,bId){
  var result={};
  if (book.chapter.hasOwnProperty('verse')){
    result[book.chapter.id]={};
    result[book.chapter.id].verse=parseBookChapterVerse(book.chapter.verse,bId,book.chapter.id);
  } else{
    for (const chapter of book.chapter) {
      result[chapter.id]={};
      result[chapter.id].verse=parseBookChapterVerse(chapter.verse,bId,chapter.id);
      // try{
      //   for (const verse of chapter.verse) {
      //     // console.log(verse);
      //   }
      // } catch(e){
      //   console.log(bId);
      //   result[chapter.id]='no verse';
      // }
      // if (!chapter.verse){
      //   // console.log('no verse')
      //   result[chapter.id]='no verse';
      // }
    }
  }
  return result;
},
parseBookChapterVerse = function(data,bId,cId){
  // NOTE expected text, id, merge, title, ref
  // NOTE bid cid, vid, text, title, ref, merge
  // var quoteStart = /“/g, quoteEnd = /”/;
  // var quoteFind = /"/g;
  try{
    var result={};
    for (const verse of data) {
      if (verse.text){
        result[verse.id]=verse;
        // var mms = verse.text.match(/"(.*?)"/);
        var quotes = verse.text.match(/"/g);
        // var quotes = verse.text.match(/'/g);
        // var mms = verse.text.match(/("([^"]|"")*")/g);
        // console.log(mms.length);
        // if (mms) {
        //   // console.log(mms);
        // }
        if (quotes) {
          if ((quotes.length % 2)){
            console.log('... single quotes:',bId,cId,verse.id,quotes.length)
          }
        }
        delete verse.id;
      } else {
        console.log('... no verse:',bId,cId,verse.id);
      }
      // result[verse.id]=verse;
    }
    return result;
  } catch(e){
    console.log('... Please check at book',bId,'chapter',cId);
    console.log(e);
    process.exit(1);
  }
},
databaseConnection = null,
databasePrepare = function(data){
  return new Promise((resolve, reject) => {
    var db = bookTargetSQLite.replace('*',bookId);
    fs.exists(db, function(e) {
      if (e) fs.unlinkSync(db);
    });

    // databaseConnection = new sqlite3.Database(':memory:');
    databaseConnection = new sqlite3.Database(db);

    databaseConnection.serialize(function() {
      // NOTE: testament
      databaseConnection.run("CREATE TABLE IF NOT EXISTS testament (id INTEGER, name TEXT, shortname TEXT)");
      // NOTE: book
      databaseConnection.run("CREATE TABLE IF NOT EXISTS book (id INTEGER, name TEXT, shortname TEXT, description TEXT)");
      // NOTE: bible
      databaseConnection.run("CREATE TABLE IF NOT EXISTS bible (bid INTEGER, cid INTEGER, vid INTEGER, verse TEXT, merged INTEGER, title TEXT, ref TEXT)");
      // NOTE: prepare insert
      databaseInsert(data).then(()=>{
        resolve()
      },(e)=>{
        reject(e);
      }).then(()=>{
        databaseConnection.close();
      })
    })
  });
},
databaseTestament = function(value){
  return new Promise((resolve, reject) => {
    var table = databaseConnection.prepare("INSERT INTO testament (id, name, shortname) VALUES (?,?,?)");
    for (const o of value) {
      table.run([o.id, o.name, o.shortname]);
    }
    table.finalize(()=>{
      resolve()
    });
  })
},
databaseBook = function(value){
  return new Promise((resolve, reject) => {
    var table = databaseConnection.prepare("INSERT INTO book (id, name, shortname, description) VALUES (?,?,?,?)");
    for (const id in value) {
      if (value.hasOwnProperty(id)) {
        const book = value[id];
        table.run([book.info.id, book.info.name, book.info.shortname, book.info.description]);
      }
    }
    table.finalize(()=>{
      resolve()
    });
  })
},
databaseInsert = function(value){
  return new Promise((resolve, reject) => {
    let taskPrimary = [];

    taskPrimary.push(databaseTestament(value.testament));
    taskPrimary.push(databaseBook(value.book));

    let bible = value.bible;
    for (const bId in bible) {
      if (bible.hasOwnProperty(bId)) {
        var book = bible[bId];
        for (const cId in book) {
          if (book.hasOwnProperty(cId)) {
            const chapter = book[cId];
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
databaseBibleCurrentBook=0,
databaseBible = function(bId, cId, chapter){
  return new Promise((resolve, reject) => {
    var table = databaseConnection.prepare("INSERT INTO bible (bid, cid, vid, verse, merged, title, ref) VALUES (?,?,?,?,?,?,?)");
    for (const vId in chapter) {
      if (chapter.hasOwnProperty(vId)) {
        const verse = chapter[vId];
        verse.merge = (verse.merge)?verse.merge:null;
        verse.title = (verse.title)?verse.title:null;
        verse.ref = (verse.ref)?verse.ref:null;
        table.run([bId,cId, Number(vId),verse.text, verse.merge,verse.title,verse.ref]);
      }
    }
    table.finalize(()=>{
      if (databaseBibleCurrentBook < bId) {
        databaseBibleCurrentBook = bId;

        process.stdout.write(`\n \x1b[2mBook\x1b[8m:\x1b[35m${bId}\x1b[0m > \x1b[2mchapter\x1b[8m:\x1b[33m${cId}\x1b[0m`);
      } else {
        process.stdout.write(` \x1b[33m${cId}\x1b[0m`);
      }
      resolve()
    })
  });
},
bookCollectionUpdate = function(books,result,callback){
  books.updated = new Date();
  books.version++;
  var bookIndex = books.book.findIndex((x)=>x.identify==bookId);
  if (bookIndex >= 0) {
    books.book[bookIndex]=result.info;
  } else {
    books.book.push(result.info)
  }
  fs.writeFile(bookCollectionJSON, JSON.stringify(books, null, 2),callback);
};

return new Promise(function(resolve, reject) {
  try {
    var bookConfiguration=fs.readFileSync(bookCollectionJSON).toString();
    resolve(JSON.parse(bookConfiguration));
  } catch (e) {
    resolve([])
  }
}).then(function(books){
  // console.log(books);
  xmlRead().then(function(result){
    // console.log(result);
    // console.log(result.bible[66][22][21]);
    new Promise(function(resolve, reject) {
      if (args.length > 1) {
        if (args[1] == 'sqlite'){
          // NOTE: create SQLite
          databasePrepare(result).then(function(){
            resolve();
            console.log('SQLite process complete',bookId,result.info.name);
          },function(e){
            reject(e);
          });
        } else if (args[1] == 'json') {
          // NOTE: Create JSON
          jsonPrepare(result).then(function(){
            resolve();
            console.log('JSON process complete',bookId,result.info.name);
          },function(e){
            reject(e);
          });
        } else {
          reject('... json/sqlite are only available tasks');
        }
      } else {
        reject('... sqlite/json');
      }
    }).then(function(){
      bookCollectionUpdate(books,result,function(e,r){
        if (e) {
          console.log(e);
        } else {
          console.log('Updated book.json');
        }
      });
    },function(error){
      console.log(error);
    });

  },function(error){
    console.log(error);
  })
},function(e){
  console.log(e)
});

// "name": "Bible in Basic English",
// "shortname": "BBE",
// "des": "",
// "copyright": "",
// "year": "1949",
// "lang": "en",
// "gId":"0B_7bPVufJ-j4b3ZiRFBPQkZZbXM"


/*
new Promise(function(resolve, reject) {
  try {
    var tmp=fs.readFileSync(bookCollectionJSON).toString();
    resolve(JSON.parse(tmp));
  } catch (e) {
    resolve({})
  }
}).then(function(books){
  xmlRead().then(function(result){
    // console.log('Completed',bookId,result.info.name);
    new Promise(function(resolve, reject) {
      // bookId = args[0],
      if (args.length > 1) {
        if (args[1] == 'sqlite'){
          // NOTE: create SQLite
          databasePrepare(result).then(function(){
            resolve();
            console.log('SQLite process complete',Number(bookId),result.info.name);
          },function(e){
            reject(e);
          });
        } else if (args[1] == 'json') {
          // NOTE: Create JSON
          jsonPrepare(result).then(function(){
            resolve();
            console.log('JSON process complete',Number(bookId),result.info.name);
          },function(e){
            reject(e);
          });
        } else {
          reject('... json/sqlite are only available tasks');
        }
      } else {
        reject('... sqlite/json');
      }
    }).then(function(){

      books[bookId]=result.info;
      fs.writeFile(bookCollectionJSON, JSON.stringify(books, null, 2),function(e,r){
        if (e) {
          console.log(e);
        } else {
          console.log('Updated book.json');
        }
      });
    },function(error){
      console.log(error);
    })
  },function(e){
    console.log(e);
  })
},function(e){
  console.log(e)
});
*/
// npm install https://github.com/mapbox/node-sqlite3/tarball/master --save-dev
