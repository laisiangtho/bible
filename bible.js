var path = require('path');
var fs = require('fs-extra');
var args = process.argv.slice(2);
// args.unshift('tmp');
/**
 * NOTE: node bible {filename:1/2/3} {option:sqlite,json} {true}
 * if option is json then there is thrid argument JSON.stringify would format
 * node bible json/ph4/xml identify
 * xml: xml->json
 * json: json->sqlite
 * scan: ?->json
 * sqlite: ?
 *  */
try{
  var task = require('./0'.replace(0,args[0]));
} catch(e){
  console.log(`\n ...\x1b[31m${args[0]}\x1b[0m?`)
  process.exit(1);
}
var currentDirectory = path.dirname(require.main.filename),
currentPath = process.cwd(),
bookCollection={},
bookCollectionJSON= path.resolve(currentDirectory,'book.json'),
settings={
  args: args,
  bookIdentify: '',
  currentDirectory: currentDirectory,
  bookSourceXML: path.resolve(currentDirectory,'xml','*.xml'),
  bookSourceJSON: path.resolve(currentDirectory,'json','*.json'),
  bookSourceSQLite: path.resolve(currentDirectory,'ph4','*.SQLite3'),
  bookTargetSQLite: path.resolve(currentDirectory,'sqlite','*.db'),
  message:{
    book: function(bId,cId){
      var bTc = (bId < 10)?' ':'';
      process.stdout.write(`\n....\x1b[2mBook\x1b[8m:\x1b[35m${bTc}${bId}\x1b[0m > \x1b[2mchapter\x1b[8m:`);
      if (cId){
        if (cId instanceof Array){
          this.chapter(cId.join(' '));
        } else {
          this.chapter(cId);
        }
      }
    },
    chapter: function(cId){
      process.stdout.write(` \x1b[33m${cId}\x1b[0m`);
    }
  }
},
bookCollectionUpdate = function(result,callback){
  var tmp = path.basename(bookCollectionJSON);
  // var resultProcess=['xml','json','sqlite'];
  if (result instanceof Object && result.info){
    bookCollection.updated = new Date();
    bookCollection.version++;
    if (result.task){
      if (!bookCollection.hasOwnProperty('collection'))bookCollection.collection={};
      for (const resultTaskId of result.task) {
        if (!bookCollection.collection.hasOwnProperty(resultTaskId)){
          bookCollection.collection[resultTaskId]=[];
        }
        if (bookCollection.collection[resultTaskId].indexOf(settings.bookIdentify) < 0){
          bookCollection.collection[resultTaskId].push(settings.bookIdentify);
        }
      }
    }
    var bookIndex = bookCollection.book.findIndex((x)=>x.identify==settings.bookIdentify);
    if (bookIndex >= 0) {
      bookCollection.book[bookIndex]=result.info;
    } else {
      bookCollection.book.push(result.info)
    }
    fs.writeFile(bookCollectionJSON, JSON.stringify(bookCollection, null, 2),function(e){
      if (e) {
        callback(e);
      } else {
        callback(`...updated\x1b[32m ${tmp}\x1b[0m`);
      }
    });
  } else {
    callback(`...skip writing\x1b[35m ${tmp}\x1b[0m`);
  }
},
taskList=[],
taskListFilter={
  fill:function(tasks){
    // NOTE: items that not available in target collection
    if (tasks && bookCollection.collection.hasOwnProperty(args[0]) && bookCollection.collection.hasOwnProperty(tasks)){
      // var src = bookCollection.collection.json, tar = bookCollection.collection.sqlite;
      var src = bookCollection.collection[args[0]], tar = bookCollection.collection[tasks];
      return src.filter(tS => (tar.indexOf(tS) === -1));
    }
  },
  all:function(tasks){
    // NOTE: all
    if (tasks && bookCollection.collection.hasOwnProperty(args[0])){
      return bookCollection.collection[args[0]];
    }
  },
  list:function(tasks){
    // NOTE: list with comma seperated
    if (tasks && /\,/.test(tasks)){
      return tasks.split(',')
    }
  }
},
taskListValidate=function(){
  // node bible xml all:json 1
  // node bible json all:sqlite
  // node bible xml fill:json 1
  // node bible json fill:sqlite
  // node bible ph4 list:a,b,c,c
  var taskId = args[1], taskMulti = /:/.test(taskId);
  taskList=[taskId];
  if (taskMulti) {
    var tmp = taskId.split(':');
    if (taskListFilter.hasOwnProperty(tmp[0])){
      taskList = taskListFilter[tmp[0]](tmp[1]);
    }
  }
},

taskInitiate=function(){
  if (taskList.length){
    taskProcess(taskList.shift());
  } else {
    console.log(`\n..Finish!`);
  }
},
taskProcess=function(taskId){
  settings.bookIdentify = taskId;
  settings.bookCollection = bookCollection;
  console.log(`\n..bookIdentify:\x1b[36m ${settings.bookIdentify}\x1b[0m`)
  return task.main(settings).then(function(response){
    bookCollectionUpdate(response,(e) => {
      console.log(e);
      taskInitiate();
    });
  },function(e){
    console.log(e);
    taskInitiate();
  });
};

new Promise(function(resolve, reject) {
  try {
    var tmp = fs.readFileSync(bookCollectionJSON).toString();
    bookCollection = JSON.parse(tmp);
    resolve();
  } catch (e) {
    reject(`...no\x1b[35m book collection\x1b[0m provided?`);
  }
}).then(function(){
  taskListValidate();
  taskInitiate();
},function(e){
  console.log(e)
});