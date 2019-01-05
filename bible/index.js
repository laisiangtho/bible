const path = require('path'), fs = require('fs'), xml2js = require('xml2js'), sqlite3 = require('sqlite3');
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
bookSource= path.resolve(currentDirectory,'src','*.xml'),
bookTargetJSON = path.resolve(currentDirectory,'json','*.json'),
bookTargetSQLite = path.resolve(currentDirectory,'db','*.db'),
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
  var result={};
  // console.log(data.info)
  // result.info = data.info;
  result.info = parseInfo(data.info);
  parseBook(data.book);
  // result.author = info(data.author);
  // result.modification = data.modification;
  // result.testament = testament(data.testament);
  // result.book = testament(data.book);
  // result.section = data.section.row;
  // result.category = category(data.category);
  return result;
},
parseInfo = function(data){
  var result={};
  for (var row of data) {
    if (row.hasOwnProperty('id') && row.hasOwnProperty('text')){
      result[row.id]=row.text;
    }
  }
  return result;
},
parseBook = function(data){
  for (var row of data) {
    console.log(row.id, row.name);
  }
  /*
  info{
    identify:'',
    year:'',
    name:'',
    shortname:'',
    description:'',
  }
  testament:{}
  book:{}
  chapter:{}
  */
},
// testament = function(data){
//   var result={};
//   for (var row of data.row) {
//     row.name=row.desc;
//     result[row.id]=row;
//     delete row.id;
//     delete row.desc;
//   }
//   return result;
// },
// category = function(data){
//   var result={};
//   for (var rows of data) {
//     result[rows.id]=rows.row;
//   }
//   return result;
// },
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
      databaseConnection.run("CREATE TABLE IF NOT EXISTS book (id INTEGER, name TEXT, shortname TEXT)");
      // NOTE: section
      databaseConnection.run("CREATE TABLE IF NOT EXISTS section (id INTEGER, name TEXT, desc TEXT, groupname TEXT, total INTEGER)");
      // NOTE: category
      databaseConnection.run("CREATE TABLE IF NOT EXISTS category (id INTEGER, book INTEGER, chapter INTEGER, verse TEXT, desc TEXT, tag TEXT)");
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
    for (const tId in value) {
      if (value.hasOwnProperty(tId)) {
        const o = value[tId];
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
    var table = databaseConnection.prepare("INSERT INTO book (id, name, shortname) VALUES (?,?,?)");
    for (const bId in value) {
      if (value.hasOwnProperty(bId)) {
        const o = value[bId];
        table.run([bId, o.name, o.shortname]);
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

    let categories = value.category;
    for (const sId in categories) {
      if (categories.hasOwnProperty(sId)) {
        var category = categories[sId];
        var section = value.section.filter(o => o.id == sId)[0];
        taskPrimary.push(databaseCategoryChildren(Number(sId),section,category));
      }
    }
    Promise.all(taskPrimary).then(()=>{
      resolve();
    }).catch(error=>{
      reject(error);
    })
  });
},
databaseCategoryChildren = function(sId,section,category){
  return new Promise((resolve, reject) => {
    let taskPrimary = [];
    let total = 0;
    var table = databaseCategoryInsert();
    for (const o of category) {
      taskPrimary.push(new Promise((resolve, reject) => {
        table.run([sId, o.book, o.chapter, o.verse, o.desc, o.tag],()=>{
          ++total;
          resolve();
        });
      }));
    }
    Promise.all(taskPrimary).then(()=>{
      table.finalize(()=>{
        databaseSectionInsert().run([sId, section.name, section.desc, section.group, total]).finalize(()=>{
          resolve();
          console.log(sId, section.name, total);
        });
      });
    }).catch(error=>{
      reject(error)
    })
  });
},
databaseCategoryInsert = function() {
  return databaseConnection.prepare("INSERT INTO category (id, book,chapter,verse, desc, tag) VALUES (?,?,?,?,?,?)");
},
databaseSectionInsert = function() {
  return databaseConnection.prepare('INSERT INTO section (id, name, desc, groupname, total) VALUES (?,?,?,?,?)');
};

// console.log(args);
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
    console.log(result);
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
